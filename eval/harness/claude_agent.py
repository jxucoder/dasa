"""Claude API agent for the DASA evaluation harness.

Requires: anthropic SDK (pip install anthropic).
Set ANTHROPIC_API_KEY environment variable.

Two variants:
  - ClaudeVanillaAgent: raw Claude with no DASA tools
  - ClaudeDasaAgent: Claude with DASA tool descriptions (profile/check/run/context)
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .agent import AgentWrapper


DASA_SYSTEM_PROMPT = """\
You are a data science agent working with Jupyter notebooks.
You have access to the DASA toolkit which provides these commands:

- `dasa profile <notebook> --var <name>` — Profile a DataFrame variable (columns, types, stats, quality issues)
- `dasa profile <notebook>` — List all DataFrames in the notebook
- `dasa profile --file data.csv` — Profile a CSV file directly
- `dasa check <notebook>` — Check notebook health (state consistency, dependencies, staleness)
- `dasa check <notebook> --fix` — Auto-fix stale/unexecuted cells
- `dasa run <notebook> --cell <N>` — Execute a specific cell with rich error context
- `dasa run <notebook> --all` — Execute all cells
- `dasa context` — Read project context and memory

When given a task, analyze the notebook and data, use DASA tools as needed,
and provide your answer. If you need to modify the notebook, return the
modified notebook JSON.
"""

VANILLA_SYSTEM_PROMPT = """\
You are a data science agent working with Jupyter notebooks.
When given a task, analyze the notebook and data, and provide your answer.
If you need to modify the notebook, return the modified notebook JSON.
"""


def _call_claude(
    system: str,
    prompt: str,
    model: str = "claude-sonnet-4-5-20250929",
    max_tokens: int = 4096,
) -> str:
    """Call the Anthropic API and return the text response."""
    try:
        import anthropic
    except ImportError:
        raise RuntimeError(
            "anthropic SDK not installed. Run: pip install anthropic"
        )

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY environment variable not set")

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


class ClaudeVanillaAgent(AgentWrapper):
    """Claude agent without DASA tools (baseline)."""

    def __init__(self, model: str = "claude-sonnet-4-5-20250929"):
        super().__init__(name=f"claude-vanilla-{model.split('-')[1]}")
        self.model = model

    def run(
        self,
        prompt: str,
        notebook: dict,
        context: dict[str, Any] | None = None,
    ) -> tuple[dict, str]:
        nb_summary = self._summarize_notebook(notebook)
        full_prompt = f"{prompt}\n\nNotebook summary:\n{nb_summary}"

        if context and context.get("data_dir"):
            full_prompt += f"\n\nData directory: {context['data_dir']}"

        response = _call_claude(
            VANILLA_SYSTEM_PROMPT,
            full_prompt,
            model=self.model,
        )

        # Try to extract modified notebook from response
        modified_nb = self._extract_notebook(response, notebook)
        return modified_nb, response

    def _summarize_notebook(self, notebook: dict) -> str:
        """Create a compact text summary of the notebook."""
        cells = notebook.get("cells", [])
        parts = []
        for i, cell in enumerate(cells):
            ctype = cell.get("cell_type", "unknown")
            source = cell.get("source", "")
            if isinstance(source, list):
                source = "".join(source)
            ec = cell.get("execution_count")
            ec_str = f" [exec: {ec}]" if ec else ""

            # Truncate long cells
            if len(source) > 500:
                source = source[:500] + "..."

            parts.append(f"Cell {i} ({ctype}{ec_str}):\n{source}")

        return "\n\n".join(parts)

    def _extract_notebook(self, response: str, original: dict) -> dict:
        """Try to extract a modified notebook JSON from the response."""
        # Look for JSON blocks
        import re
        json_blocks = re.findall(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
        for block in json_blocks:
            try:
                parsed = json.loads(block)
                if "cells" in parsed:
                    return parsed
            except json.JSONDecodeError:
                continue
        return self.clone_notebook(original)


class ClaudeDasaAgent(AgentWrapper):
    """Claude agent with DASA tools available.

    This agent includes DASA tool descriptions in its system prompt,
    and can optionally execute DASA commands via subprocess.
    """

    def __init__(
        self,
        model: str = "claude-sonnet-4-5-20250929",
        execute_tools: bool = False,
    ):
        super().__init__(name=f"claude-dasa-{model.split('-')[1]}")
        self.model = model
        self.execute_tools = execute_tools

    def run(
        self,
        prompt: str,
        notebook: dict,
        context: dict[str, Any] | None = None,
    ) -> tuple[dict, str]:
        nb_path = context.get("notebook_path", "notebook.ipynb") if context else "notebook.ipynb"
        data_dir = context.get("data_dir", "") if context else ""

        # Pre-run DASA tools to build context
        dasa_context = ""
        if self.execute_tools:
            dasa_context = self._run_dasa_tools(nb_path, data_dir)

        vanilla = ClaudeVanillaAgent(model=self.model)
        nb_summary = vanilla._summarize_notebook(notebook)

        full_prompt = prompt
        full_prompt += f"\n\nNotebook summary:\n{nb_summary}"
        if dasa_context:
            full_prompt += f"\n\nDASA tool output:\n{dasa_context}"
        if data_dir:
            full_prompt += f"\n\nData directory: {data_dir}"

        response = _call_claude(
            DASA_SYSTEM_PROMPT,
            full_prompt,
            model=self.model,
        )

        modified_nb = vanilla._extract_notebook(response, notebook)
        return modified_nb, response

    def _run_dasa_tools(self, nb_path: str, data_dir: str) -> str:
        """Pre-run DASA tools and collect their output."""
        outputs = []

        # Run dasa check
        try:
            result = subprocess.run(
                ["dasa", "check", nb_path, "--format", "json"],
                capture_output=True, text=True, timeout=60,
            )
            if result.stdout.strip():
                outputs.append(f"## dasa check\n{result.stdout.strip()}")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # Run dasa profile (list DataFrames)
        try:
            result = subprocess.run(
                ["dasa", "profile", nb_path, "--format", "json"],
                capture_output=True, text=True, timeout=120,
            )
            if result.stdout.strip():
                outputs.append(f"## dasa profile\n{result.stdout.strip()}")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # Profile CSV files in data dir
        if data_dir:
            data_path = Path(data_dir)
            if data_path.exists():
                for csv_file in data_path.glob("*.csv"):
                    try:
                        result = subprocess.run(
                            ["dasa", "profile", "--file", str(csv_file), "--format", "json"],
                            capture_output=True, text=True, timeout=30,
                        )
                        if result.stdout.strip():
                            outputs.append(f"## dasa profile --file {csv_file.name}\n{result.stdout.strip()}")
                    except (subprocess.TimeoutExpired, FileNotFoundError):
                        pass

        return "\n\n".join(outputs)

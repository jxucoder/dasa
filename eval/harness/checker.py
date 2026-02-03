"""Task result checking."""

import json
import re
from pathlib import Path
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .runner import Task


class TaskChecker:
    """Checks if task responses meet expected criteria."""

    def check(
        self,
        task: "Task",
        response: str,
        notebook_path: Optional[Path] = None
    ) -> bool:
        """Check if the response satisfies the task requirements."""

        check_type = task.check_type
        expected = task.expected_answer

        if check_type == "contains":
            return self._check_contains(response, expected)

        elif check_type == "contains_all":
            return self._check_contains_all(response, expected)

        elif check_type == "json_match":
            return self._check_json_match(response, expected)

        elif check_type == "cell_executes":
            return self._check_cell_executes(notebook_path, task.target_cell)

        elif check_type == "notebook_executes":
            return self._check_notebook_executes(notebook_path)

        elif check_type == "notebook_reproducible":
            return self._check_notebook_reproducible(notebook_path)

        elif check_type == "has_plot_output":
            return self._check_has_plot(notebook_path)

        else:
            raise ValueError(f"Unknown check type: {check_type}")

    def _check_contains(self, response: str, expected: str) -> bool:
        """Check if response contains the expected string."""
        return expected.lower() in response.lower()

    def _check_contains_all(self, response: str, expected: list) -> bool:
        """Check if response contains all expected items."""
        response_lower = response.lower()

        for item in expected:
            item_str = str(item).lower()
            if item_str not in response_lower:
                return False

        return True

    def _check_json_match(self, response: str, expected: dict) -> bool:
        """Check if response contains matching JSON structure."""
        # Try to extract JSON from response
        try:
            # Look for JSON-like content
            json_match = re.search(r'\{[^{}]*\}', response)
            if json_match:
                parsed = json.loads(json_match.group())
                return self._dict_match(parsed, expected)
        except json.JSONDecodeError:
            pass

        # Fallback: check if all key-value pairs are mentioned
        for key, value in expected.items():
            if str(key).lower() not in response.lower():
                return False
            if str(value).lower() not in response.lower():
                return False

        return True

    def _dict_match(self, actual: dict, expected: dict) -> bool:
        """Check if actual dict matches expected dict."""
        for key, value in expected.items():
            if key not in actual:
                return False
            if isinstance(value, dict):
                if not isinstance(actual[key], dict):
                    return False
                if not self._dict_match(actual[key], value):
                    return False
            elif isinstance(value, list):
                if not isinstance(actual[key], list):
                    return False
                if set(actual[key]) != set(value):
                    return False
            else:
                if actual[key] != value:
                    return False
        return True

    def _check_cell_executes(
        self,
        notebook_path: Optional[Path],
        target_cell: Optional[int]
    ) -> bool:
        """Check if the target cell executes without error."""
        if not notebook_path or not notebook_path.exists():
            return False

        try:
            import nbformat
            from nbclient import NotebookClient

            with open(notebook_path) as f:
                nb = nbformat.read(f, as_version=4)

            client = NotebookClient(nb, timeout=60)

            # Execute cells up to and including target
            if target_cell is not None:
                for i in range(target_cell + 1):
                    client.execute_cell(nb.cells[i], i)

            return True

        except Exception:
            return False

    def _check_notebook_executes(self, notebook_path: Optional[Path]) -> bool:
        """Check if the entire notebook executes without error."""
        if not notebook_path or not notebook_path.exists():
            return False

        try:
            import nbformat
            from nbclient import NotebookClient

            with open(notebook_path) as f:
                nb = nbformat.read(f, as_version=4)

            client = NotebookClient(nb, timeout=300)
            client.execute()

            return True

        except Exception:
            return False

    def _check_notebook_reproducible(self, notebook_path: Optional[Path]) -> bool:
        """Check if notebook produces same results on multiple runs."""
        if not notebook_path or not notebook_path.exists():
            return False

        try:
            import nbformat
            from nbclient import NotebookClient

            with open(notebook_path) as f:
                nb = nbformat.read(f, as_version=4)

            # Run twice and compare outputs
            results = []
            for _ in range(2):
                nb_copy = nbformat.read(open(notebook_path), as_version=4)
                client = NotebookClient(nb_copy, timeout=300)
                client.execute()

                # Collect outputs
                outputs = []
                for cell in nb_copy.cells:
                    if cell.cell_type == "code":
                        outputs.append(str(cell.get("outputs", [])))
                results.append(outputs)

            # Compare
            return results[0] == results[1]

        except Exception:
            return False

    def _check_has_plot(self, notebook_path: Optional[Path]) -> bool:
        """Check if notebook has plot output."""
        if not notebook_path or not notebook_path.exists():
            return False

        try:
            import nbformat

            with open(notebook_path) as f:
                nb = nbformat.read(f, as_version=4)

            for cell in nb.cells:
                if cell.cell_type == "code":
                    for output in cell.get("outputs", []):
                        # Check for image output
                        if output.get("output_type") == "display_data":
                            data = output.get("data", {})
                            if "image/png" in data or "image/svg+xml" in data:
                                return True

            return False

        except Exception:
            return False

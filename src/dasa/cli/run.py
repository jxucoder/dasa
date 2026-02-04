"""Run command implementation."""

import ast
import difflib
import json
import os
import re
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import typer
from rich.console import Console

from dasa.notebook.jupyter import JupyterAdapter
from dasa.notebook.kernel import KernelManager, ExecutionResult
from dasa.notebook.base import Cell

console = Console()


def get_jobs_dir() -> Path:
    """Get the jobs directory."""
    jobs_dir = Path.home() / ".dasa" / "jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)
    return jobs_dir


def run(
    notebook: str = typer.Argument(..., help="Path to notebook"),
    cell: Optional[int] = typer.Option(None, "--cell", "-c", help="Run specific cell"),
    from_cell: Optional[int] = typer.Option(None, "--from", help="Run from cell N to end"),
    to_cell: Optional[int] = typer.Option(None, "--to", help="Run from start to cell N"),
    all_cells: bool = typer.Option(False, "--all", help="Run all cells"),
    stale: bool = typer.Option(False, "--stale", help="Run stale cells only"),
    timeout: int = typer.Option(300, "--timeout", "-t", help="Timeout in seconds"),
    async_run: bool = typer.Option(False, "--async", help="Run in background"),
    format_output: str = typer.Option("text", "--format", "-f", help="Output format"),
) -> None:
    """Execute notebook cells."""

    if async_run:
        _run_async(notebook, cell, from_cell, to_cell, all_cells, stale, timeout)
        return

    _run_sync(notebook, cell, from_cell, to_cell, all_cells, stale, timeout, format_output)


def _run_async(
    notebook: str,
    cell: Optional[int],
    from_cell: Optional[int],
    to_cell: Optional[int],
    all_cells: bool,
    stale: bool,
    timeout: int
) -> None:
    """Run cells in background."""

    # Generate job ID
    job_id = f"nb_{uuid.uuid4().hex[:8]}"
    jobs_dir = get_jobs_dir()
    job_file = jobs_dir / f"{job_id}.json"
    log_file = jobs_dir / f"{job_id}.log"

    # Build command for subprocess
    cmd = [sys.executable, "-m", "dasa.cli.async_runner"]
    cmd.extend(["--notebook", notebook])
    cmd.extend(["--job-id", job_id])
    cmd.extend(["--timeout", str(timeout)])

    if cell is not None:
        cmd.extend(["--cell", str(cell)])
    if from_cell is not None:
        cmd.extend(["--from-cell", str(from_cell)])
    if to_cell is not None:
        cmd.extend(["--to-cell", str(to_cell)])
    if all_cells:
        cmd.append("--all")
    if stale:
        cmd.append("--stale")

    # Create initial job record
    job_data = {
        "id": job_id,
        "notebook": notebook,
        "cell": cell,
        "status": "starting",
        "started": datetime.now().isoformat(),
        "pid": None,
        "progress": "0%"
    }
    job_file.write_text(json.dumps(job_data, indent=2))

    # Start background process
    with open(log_file, "w") as log:
        process = subprocess.Popen(
            cmd,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True
        )

    # Update job with PID
    job_data["pid"] = process.pid
    job_data["status"] = "running"
    job_file.write_text(json.dumps(job_data, indent=2))

    console.print(f"\n[bold green]Started background job:[/bold green] {job_id}")
    console.print(f"  Notebook: {notebook}")
    if cell is not None:
        console.print(f"  Cell: {cell}")
    elif all_cells:
        console.print(f"  Cells: all")
    console.print(f"\n[dim]Check status:[/dim]  dasa status {job_id}")
    console.print(f"[dim]View output:[/dim]   dasa result {job_id}")
    console.print(f"[dim]Cancel:[/dim]        dasa cancel {job_id}")


def _run_sync(
    notebook: str,
    cell: Optional[int],
    from_cell: Optional[int],
    to_cell: Optional[int],
    all_cells: bool,
    stale: bool,
    timeout: int,
    format_output: str
) -> None:
    """Run cells synchronously."""

    adapter = JupyterAdapter(notebook)
    kernel = KernelManager(adapter.kernel_spec or "python3")

    try:
        kernel.start()

        # Determine which cells to run
        cells_to_run = _get_cells_to_run(
            adapter, cell, from_cell, to_cell, all_cells, stale
        )

        if not cells_to_run:
            console.print("[yellow]No cells to run[/yellow]")
            return

        results = []

        for cell_obj in cells_to_run:
            console.print(f"Running Cell {cell_obj.index}...", end=" ")

            start = time.time()
            result = kernel.execute(cell_obj.source, timeout=timeout)
            elapsed = time.time() - start

            if result.success:
                console.print(f"[green]OK[/green] ({elapsed:.2f}s)")
            else:
                console.print(f"[red]FAILED[/red] ({elapsed:.2f}s)")

            # Show detailed result
            _show_execution_result(
                cell_obj.index,
                result,
                elapsed,
                cell_obj.source,
                kernel,
                format_output
            )

            results.append({
                "cell": cell_obj.index,
                "success": result.success,
                "elapsed": elapsed
            })

        # Summary
        success_count = sum(1 for r in results if r["success"])
        console.print(f"\n[bold]Summary:[/bold] {success_count}/{len(results)} cells succeeded")

    finally:
        kernel.shutdown()


def _get_cells_to_run(
    adapter: JupyterAdapter,
    cell: Optional[int],
    from_cell: Optional[int],
    to_cell: Optional[int],
    all_cells: bool,
    stale: bool
) -> list[Cell]:
    """Determine which cells to run based on options."""

    code_cells = adapter.code_cells

    if cell is not None:
        # Run single cell
        return [c for c in code_cells if c.index == cell]

    if all_cells:
        return code_cells

    if from_cell is not None:
        return [c for c in code_cells if c.index >= from_cell]

    if to_cell is not None:
        return [c for c in code_cells if c.index <= to_cell]

    if stale:
        # Return cells with no execution count
        return [c for c in code_cells if c.execution_count is None]

    # Default: no cells (require explicit selection)
    return []


def _show_execution_result(
    cell_index: int,
    result: ExecutionResult,
    elapsed: float,
    source: str,
    kernel: KernelManager,
    format_output: str
) -> None:
    """Show detailed execution result."""

    if format_output == "json":
        console.print(json.dumps({
            "cell": cell_index,
            "success": result.success,
            "elapsed_seconds": elapsed,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "error": result.error,
            "error_type": result.error_type
        }, indent=2))
        return

    # Show stdout
    if result.stdout:
        console.print("\n[dim]Output:[/dim]")
        for line in result.stdout.strip().split('\n')[:15]:
            console.print(f"  {line}")
        if result.stdout.count('\n') > 15:
            console.print("  [dim]... (truncated)[/dim]")

    # Show error with context
    if not result.success:
        console.print(f"\n[red]Error: {result.error_type}: {result.error}[/red]")

        # Try to provide helpful context
        context = _build_error_context(
            result.error_type,
            result.error,
            source,
            result.traceback,
            kernel
        )

        if context.get("line"):
            console.print(f"\nLine {context['line_number']}: {context['line']}")

        if context.get("available"):
            console.print(f"\n[dim]Available: {', '.join(context['available'][:10])}[/dim]")

        if context.get("suggestion"):
            console.print(f"\n[yellow]Suggestion: {context['suggestion']}[/yellow]")


def _build_error_context(
    error_type: Optional[str],
    error_msg: Optional[str],
    source: str,
    traceback: list[str],
    kernel: KernelManager
) -> dict[str, Any]:
    """Build helpful context for an error."""

    context: dict[str, Any] = {}

    if not error_type or not error_msg:
        return context

    # Try to find the line number from traceback
    if traceback:
        for line in traceback:
            if "--->" in line or "-->" in line:
                # Extract line number
                match = re.search(r'(\d+)', line)
                if match:
                    line_num = int(match.group(1))
                    lines = source.split('\n')
                    if 0 < line_num <= len(lines):
                        context["line_number"] = line_num
                        context["line"] = lines[line_num - 1].strip()

    # Error-specific context
    if error_type == "KeyError":
        # For DataFrame column errors, show available columns
        var_match = _extract_variable_from_error(error_msg, source)
        if var_match:
            try:
                cols_code = f"list({var_match}.columns)"
                cols_result = kernel.execute(cols_code)
                if cols_result.success:
                    context["available"] = ast.literal_eval(cols_result.stdout.strip())

                    # Find similar column name
                    missing_col = error_msg.strip("'\"")
                    similar = difflib.get_close_matches(
                        missing_col, context["available"], n=1, cutoff=0.6
                    )
                    if similar:
                        context["suggestion"] = f"Did you mean '{similar[0]}'?"
            except Exception:
                pass

    elif error_type == "NameError":
        # Show what is defined
        missing_name = error_msg.split("'")[1] if "'" in error_msg else error_msg

        # Get defined names
        try:
            dir_result = kernel.execute("dir()")
            if dir_result.success:
                defined = ast.literal_eval(dir_result.stdout.strip())
                user_vars = [v for v in defined if not v.startswith('_')]

                similar = difflib.get_close_matches(
                    missing_name, user_vars, n=1, cutoff=0.6
                )
                if similar:
                    context["suggestion"] = f"Did you mean '{similar[0]}'?"
                    context["available"] = user_vars[:10]
        except Exception:
            pass

    return context


def _extract_variable_from_error(error_msg: str, source: str) -> Optional[str]:
    """Try to extract the DataFrame variable from error context."""

    # Look for patterns like df['col'] in source
    patterns = [
        r"(\w+)\s*\[",  # var[
        r"(\w+)\.loc",   # var.loc
        r"(\w+)\.iloc",  # var.iloc
    ]

    for pattern in patterns:
        matches = re.findall(pattern, source)
        if matches:
            return matches[0]

    return None

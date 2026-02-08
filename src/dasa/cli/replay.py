"""Replay command — run notebook from scratch, verify reproducibility."""

import hashlib
import json

import typer
from rich.console import Console

from dasa.notebook.jupyter import JupyterAdapter
from dasa.notebook.kernel import DasaKernelManager
from dasa.session.log import SessionLog

console = Console()


def replay(
    notebook: str = typer.Argument(..., help="Path to notebook"),
    timeout: int = typer.Option(300, "--timeout", "-t", help="Timeout per cell in seconds"),
    format: str = typer.Option("text", "--format", "-f", help="Output format: text, json"),
) -> None:
    """Run notebook from scratch in a fresh kernel and verify reproducibility."""
    adapter = JupyterAdapter(notebook)
    code_cells = adapter.code_cells

    if not code_cells:
        console.print("[yellow]No code cells found.[/yellow]")
        return

    if format != "json":
        console.print(f"\n[bold]Replaying from scratch (new kernel)...[/bold]\n")

    kernel = DasaKernelManager()
    results = []
    total_time = 0.0

    try:
        kernel.start()

        for cell in code_cells:
            result = kernel.execute(cell.source, timeout=timeout)
            total_time += result.execution_time

            cell_result = {
                "cell": cell.index,
                "success": result.success,
                "execution_time": result.execution_time,
            }

            # Compare output to saved output
            output_match = _compare_outputs(cell.outputs, result)
            cell_result["output_match"] = output_match

            if result.success:
                match_str = "outputs match" if output_match else "OUTPUT DIFFERS"
                if format != "json":
                    if output_match:
                        console.print(
                            f"  Cell {cell.index}: [green]OK[/green] "
                            f"({result.execution_time:.1f}s) - {match_str}"
                        )
                    else:
                        console.print(
                            f"  Cell {cell.index}: [yellow]![/yellow] "
                            f"({result.execution_time:.1f}s) - [yellow]{match_str}[/yellow]"
                        )
            else:
                cell_result["error_type"] = result.error_type
                cell_result["error"] = result.error

                if format != "json":
                    console.print(
                        f"  Cell {cell.index}: [red]FAILED[/red] "
                        f"({result.execution_time:.1f}s) - "
                        f"{result.error_type}: {result.error}"
                    )

                # Suggest fixes for common issues
                suggestion = _suggest_fix(result.error_type, result.error, cell.source)
                if suggestion:
                    cell_result["suggestion"] = suggestion
                    if format != "json":
                        console.print(f"    -> {suggestion}")

            results.append(cell_result)

    finally:
        kernel.shutdown()

    # Compute summary
    total_cells = len(results)
    executed = sum(1 for r in results if r["success"])
    reproduced = sum(1 for r in results if r["success"] and r.get("output_match", False))
    reproducibility_score = reproduced / total_cells * 100 if total_cells > 0 else 0

    summary = {
        "total_cells": total_cells,
        "executed": executed,
        "reproduced": reproduced,
        "reproducibility_score": round(reproducibility_score, 1),
        "total_time": round(total_time, 1),
    }

    if format == "json":
        console.print(json.dumps({"cells": results, "summary": summary}, indent=2))
    else:
        console.print(f"\n{'─' * 50}")
        console.print(f"Total time: {total_time:.1f}s")
        console.print(f"Cells executed: {executed}/{total_cells}")
        console.print(f"Reproducibility Score: {reproducibility_score:.0f}% ({reproduced}/{total_cells} cells)")

        # List issues
        issues = [r for r in results if not r["success"] or not r.get("output_match", True)]
        if issues:
            console.print(f"\n[bold]Issues Found:[/bold]")
            for i, issue in enumerate(issues, 1):
                if not issue["success"]:
                    console.print(f"  {i}. Cell {issue['cell']}: {issue.get('error_type', 'Error')}: {issue.get('error', 'unknown')}")
                else:
                    console.print(f"  {i}. Cell {issue['cell']}: Output differs from original")
                if issue.get("suggestion"):
                    console.print(f"     -> {issue['suggestion']}")
        console.print()

    # Auto-log
    log = SessionLog()
    log.append("replay", f"Replayed {notebook}. {reproducibility_score:.0f}% reproducible ({reproduced}/{total_cells})")

    if executed < total_cells:
        raise typer.Exit(1)


def _compare_outputs(saved_outputs: list, result) -> bool:
    """Compare saved outputs with execution result."""
    if not saved_outputs:
        return True  # No saved output to compare against

    # Hash the saved text outputs
    saved_text = ""
    for output in saved_outputs:
        if isinstance(output, dict):
            if output.get("output_type") == "stream":
                saved_text += output.get("text", "")
            elif output.get("output_type") in ("execute_result", "display_data"):
                data = output.get("data", {})
                saved_text += data.get("text/plain", "")

    new_text = (result.stdout or "") + (result.result or "")

    if not saved_text and not new_text:
        return True

    # Compare hashes (loose comparison)
    saved_hash = hashlib.md5(saved_text.strip().encode()).hexdigest()
    new_hash = hashlib.md5(new_text.strip().encode()).hexdigest()
    return saved_hash == new_hash


def _suggest_fix(error_type: str | None, error_msg: str | None, source: str) -> str | None:
    """Suggest fixes for common reproducibility issues."""
    if error_type == "FileNotFoundError":
        return "Check if the file exists and the path is correct (avoid hardcoded absolute paths)"

    if error_type == "ModuleNotFoundError":
        module = (error_msg or "").replace("No module named ", "").strip("'\"")
        return f"Install missing module: pip install {module}"

    if error_type == "KeyError" and "environ" in source:
        return "Set the required environment variable before running"

    if "random" in source.lower() and "seed" not in source.lower():
        return "Set random seed (e.g., np.random.seed(42)) for reproducibility"

    if error_type == "NameError":
        return "A required variable is not defined. Run cells in order from the beginning."

    return None

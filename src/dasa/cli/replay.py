"""Replay command implementation."""

import hashlib
import time
from typing import Any, Optional

import typer
from rich.console import Console

from dasa.notebook.jupyter import JupyterAdapter
from dasa.notebook.kernel import KernelManager

console = Console()


def replay(
    notebook: str = typer.Argument(..., help="Path to notebook"),
    compare: bool = typer.Option(True, "--compare/--no-compare", help="Compare outputs"),
    save: Optional[str] = typer.Option(None, "--save", "-s", help="Save replayed notebook to file"),
    strict: bool = typer.Option(False, "--strict", help="Fail on any difference"),
    timeout: int = typer.Option(300, "--timeout", "-t", help="Timeout per cell"),
    format_output: str = typer.Option("text", "--format", "-f", help="Output format"),
) -> None:
    """Run notebook from scratch and verify reproducibility."""

    adapter = JupyterAdapter(notebook)
    kernel = KernelManager(adapter.kernel_spec or "python3")

    console.print(f"\n[bold]Replaying notebook from scratch (new kernel)...[/bold]\n")

    results: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []

    try:
        kernel.start()

        for cell in adapter.code_cells:
            console.print(f"Cell {cell.index}: ", end="")

            start = time.time()
            result = kernel.execute(cell.source, timeout=timeout)
            elapsed = time.time() - start

            cell_result: dict[str, Any] = {
                "cell": cell.index,
                "preview": cell.preview,
                "success": result.success,
                "elapsed": elapsed,
                "output_match": None,
                "issue": None
            }

            if result.success:
                # Compare outputs if enabled
                if compare and cell.outputs:
                    original_hash = _hash_outputs(cell.outputs)
                    new_hash = _hash_output(result.stdout, result.result)

                    if original_hash == new_hash:
                        console.print(f"[green]OK[/green] ({elapsed:.2f}s) - outputs match")
                        cell_result["output_match"] = True
                    else:
                        console.print(f"[yellow]![/yellow] ({elapsed:.2f}s) - OUTPUT DIFFERS")
                        cell_result["output_match"] = False
                        cell_result["issue"] = "Output differs from original"
                        issues.append({
                            "cell": cell.index,
                            "type": "output_differs",
                            "message": "Output differs from original run"
                        })
                else:
                    console.print(f"[green]OK[/green] ({elapsed:.2f}s)")
                    cell_result["output_match"] = True
            else:
                console.print(f"[red]X FAILED[/red] ({elapsed:.2f}s)")
                console.print(f"    Error: {result.error_type}: {result.error}")

                cell_result["issue"] = f"{result.error_type}: {result.error}"
                issues.append({
                    "cell": cell.index,
                    "type": "execution_error",
                    "error_type": result.error_type,
                    "message": result.error
                })

            results.append(cell_result)

    finally:
        kernel.shutdown()

    # Summary
    _show_summary(results, issues, format_output)

    # Suggest fixes for issues
    if issues:
        _suggest_fixes(issues)

    # Exit code
    if strict and issues:
        raise typer.Exit(1)
    elif any(not r["success"] for r in results):
        raise typer.Exit(1)


def _hash_outputs(outputs: list[dict[str, Any]]) -> str:
    """Hash cell outputs for comparison."""
    content = ""
    for output in outputs:
        if output.get("output_type") == "stream":
            content += output.get("text", "")
        elif output.get("output_type") == "execute_result":
            content += str(output.get("data", {}))
    return hashlib.md5(content.encode()).hexdigest()


def _hash_output(stdout: str, result: Any) -> str:
    """Hash execution output for comparison."""
    content = stdout + str(result or "")
    return hashlib.md5(content.encode()).hexdigest()


def _show_summary(results: list[dict[str, Any]], issues: list[dict[str, Any]], format_output: str) -> None:
    """Show replay summary."""

    if format_output == "json":
        import json
        console.print(json.dumps({
            "results": results,
            "issues": issues,
            "summary": {
                "total": len(results),
                "succeeded": sum(1 for r in results if r["success"]),
                "matched": sum(1 for r in results if r["output_match"])
            }
        }, indent=2))
        return

    total = len(results)
    succeeded = sum(1 for r in results if r["success"])
    matched = sum(1 for r in results if r["output_match"])

    console.print(f"\n[bold]{'─' * 50}[/bold]")
    console.print(f"[bold]Total time:[/bold] {sum(r['elapsed'] for r in results):.1f}s")
    console.print(f"[bold]Cells executed:[/bold] {succeeded}/{total}")

    if total > 0:
        repro_score = matched / total * 100
        color = "green" if repro_score == 100 else "yellow" if repro_score > 80 else "red"
        console.print(f"[bold]Reproducibility Score:[/bold] [{color}]{repro_score:.0f}%[/{color}] ({matched}/{total} cells)")


def _suggest_fixes(issues: list[dict[str, Any]]) -> None:
    """Suggest fixes for reproducibility issues."""

    console.print(f"\n[bold yellow]Issues Found:[/bold yellow]")

    for i, issue in enumerate(issues, 1):
        console.print(f"\n  {i}. Cell {issue['cell']}: {issue['message']}")

        # Suggest fixes based on issue type
        if issue["type"] == "execution_error":
            if issue.get("error_type") == "FileNotFoundError":
                console.print("     [dim]-> Check if file exists and is committed to repo[/dim]")
            elif issue.get("error_type") == "ModuleNotFoundError":
                console.print("     [dim]-> Add missing package to requirements.txt[/dim]")
            elif issue.get("error_type") == "KeyError":
                console.print("     [dim]-> Check environment variables are set[/dim]")

        elif issue["type"] == "output_differs":
            console.print("     [dim]-> Set random seed with np.random.seed(42)[/dim]")
            console.print("     [dim]-> Check for non-deterministic operations[/dim]")

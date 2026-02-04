"""Result command for retrieving async job output."""

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table

console = Console()


def get_jobs_dir() -> Path:
    """Get the jobs directory."""
    jobs_dir = Path.home() / ".dasa" / "jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)
    return jobs_dir


def result(
    job_id: str = typer.Argument(..., help="Job ID to get results for"),
    cell: Optional[int] = typer.Option(None, "--cell", "-c", help="Show result for specific cell"),
    format_output: str = typer.Option("text", "--format", "-f", help="Output format"),
    show_output: bool = typer.Option(True, "--output/--no-output", help="Show cell outputs"),
    show_errors: bool = typer.Option(True, "--errors/--no-errors", help="Show errors"),
) -> None:
    """Get results from a completed async job."""

    jobs_dir = get_jobs_dir()
    job_file = jobs_dir / f"{job_id}.json"

    if not job_file.exists():
        console.print(f"[red]Job {job_id} not found[/red]")
        raise typer.Exit(1)

    job_data = json.loads(job_file.read_text())
    status = job_data.get("status", "unknown")

    if status == "running":
        console.print(f"[yellow]Job {job_id} is still running[/yellow]")
        console.print(f"Progress: {job_data.get('progress', 'unknown')}")
        console.print(f"Current cell: {job_data.get('current_cell', 'unknown')}")
        console.print("\nUse [bold]dasa status {job_id} --watch[/bold] to monitor progress")
        raise typer.Exit(2)

    if status == "starting":
        console.print(f"[blue]Job {job_id} is starting...[/blue]")
        raise typer.Exit(2)

    results = job_data.get("results", [])

    if cell is not None:
        results = [r for r in results if r.get("cell") == cell]
        if not results:
            console.print(f"[red]No results for cell {cell}[/red]")
            raise typer.Exit(1)

    if format_output == "json":
        output = {
            "job_id": job_id,
            "status": status,
            "results": results,
            "summary": job_data.get("summary")
        }
        console.print(json.dumps(output, indent=2))
        return

    # Text output
    console.print(f"\n[bold]Results for Job {job_id}[/bold]")
    console.print(f"Status: [{'green' if status == 'completed' else 'red'}]{status.upper()}[/{'green' if status == 'completed' else 'red'}]")

    if job_data.get("summary"):
        summary = job_data["summary"]
        console.print(f"Summary: {summary.get('succeeded', 0)}/{summary.get('total', 0)} cells succeeded")

    console.print()

    for r in results:
        cell_idx = r.get("cell", "?")
        success = r.get("success", False)
        status_icon = "[green]✓[/green]" if success else "[red]✗[/red]"

        console.print(f"{status_icon} [bold]Cell {cell_idx}[/bold]")

        if show_output and r.get("stdout"):
            console.print("  [dim]Output:[/dim]")
            # Show output with proper formatting
            output_lines = r["stdout"].strip().split("\n")
            for line in output_lines[:20]:  # Limit to 20 lines
                console.print(f"    {line}")
            if len(output_lines) > 20:
                console.print(f"    [dim]... ({len(output_lines) - 20} more lines)[/dim]")

        if show_errors and r.get("error"):
            console.print(f"  [red]Error: {r['error']}[/red]")

        if r.get("elapsed"):
            console.print(f"  [dim]Time: {r['elapsed']:.2f}s[/dim]")

        console.print()

    # Show log file location
    log_file = jobs_dir / f"{job_id}.log"
    if log_file.exists():
        console.print(f"[dim]Full log: {log_file}[/dim]")

"""Status command for async jobs."""

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

console = Console()


def get_jobs_dir() -> Path:
    """Get the jobs directory."""
    jobs_dir = Path.home() / ".dasa" / "jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)
    return jobs_dir


def status(
    job_id: str = typer.Argument(..., help="Job ID to check"),
    format_output: str = typer.Option("text", "--format", "-f", help="Output format"),
) -> None:
    """Check status of an async job."""

    jobs_dir = get_jobs_dir()
    job_file = jobs_dir / f"{job_id}.json"

    if not job_file.exists():
        console.print(f"[red]Job {job_id} not found[/red]")
        raise typer.Exit(1)

    job_data = json.loads(job_file.read_text())

    if format_output == "json":
        console.print(json.dumps(job_data, indent=2))
        return

    # Text output
    status = job_data.get("status", "unknown")
    status_color = {
        "running": "yellow",
        "completed": "green",
        "failed": "red",
        "cancelled": "dim"
    }.get(status, "white")

    console.print(f"\n[bold]Job {job_id}[/bold]")
    console.print(f"  Status: [{status_color}]{status.upper()}[/{status_color}]")
    console.print(f"  Notebook: {job_data.get('notebook', 'unknown')}")
    console.print(f"  Cell: {job_data.get('cell', 'unknown')}")

    if job_data.get("started"):
        console.print(f"  Started: {job_data['started']}")

    if job_data.get("completed"):
        console.print(f"  Completed: {job_data['completed']}")

    if job_data.get("progress"):
        console.print(f"  Progress: {job_data['progress']}")

    if job_data.get("error"):
        console.print(f"  [red]Error: {job_data['error']}[/red]")

    # Show output file
    output_file = jobs_dir / f"{job_id}.log"
    if output_file.exists():
        console.print(f"\n  Output log: {output_file}")

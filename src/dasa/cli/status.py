"""Status command for async jobs."""

import json
import os
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

console = Console()


def get_jobs_dir() -> Path:
    """Get the jobs directory."""
    jobs_dir = Path.home() / ".dasa" / "jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)
    return jobs_dir


def status(
    job_id: Optional[str] = typer.Argument(None, help="Job ID to check (omit to list all)"),
    format_output: str = typer.Option("text", "--format", "-f", help="Output format"),
    watch: bool = typer.Option(False, "--watch", "-w", help="Watch for updates"),
) -> None:
    """Check status of async jobs."""

    jobs_dir = get_jobs_dir()

    if job_id is None:
        # List all jobs
        _list_all_jobs(jobs_dir, format_output)
        return

    job_file = jobs_dir / f"{job_id}.json"

    if not job_file.exists():
        console.print(f"[red]Job {job_id} not found[/red]")
        raise typer.Exit(1)

    if watch:
        _watch_job(job_id, jobs_dir)
    else:
        _show_job_status(job_id, jobs_dir, format_output)


def _list_all_jobs(jobs_dir: Path, format_output: str) -> None:
    """List all jobs."""

    job_files = list(jobs_dir.glob("*.json"))

    if not job_files:
        console.print("[dim]No jobs found[/dim]")
        return

    jobs = []
    for job_file in sorted(job_files, key=lambda f: f.stat().st_mtime, reverse=True):
        try:
            job_data = json.loads(job_file.read_text())
            jobs.append(job_data)
        except Exception:
            pass

    if format_output == "json":
        console.print(json.dumps(jobs, indent=2))
        return

    # Table output
    table = Table(title="Background Jobs")
    table.add_column("Job ID", style="cyan")
    table.add_column("Status")
    table.add_column("Notebook")
    table.add_column("Progress")
    table.add_column("Started")

    for job in jobs[:10]:  # Show last 10
        status_val = job.get("status", "unknown")
        status_color = {
            "running": "yellow",
            "completed": "green",
            "failed": "red",
            "cancelled": "dim",
            "starting": "blue"
        }.get(status_val, "white")

        table.add_row(
            job.get("id", "?"),
            f"[{status_color}]{status_val}[/{status_color}]",
            Path(job.get("notebook", "?")).name,
            job.get("progress", "-"),
            job.get("started", "-")[:19] if job.get("started") else "-"
        )

    console.print(table)


def _show_job_status(job_id: str, jobs_dir: Path, format_output: str) -> None:
    """Show status of a specific job."""

    job_file = jobs_dir / f"{job_id}.json"
    job_data = json.loads(job_file.read_text())

    if format_output == "json":
        console.print(json.dumps(job_data, indent=2))
        return

    # Text output
    status_val = job_data.get("status", "unknown")
    status_color = {
        "running": "yellow",
        "completed": "green",
        "failed": "red",
        "cancelled": "dim"
    }.get(status_val, "white")

    console.print(f"\n[bold]Job {job_id}[/bold]")
    console.print(f"  Status: [{status_color}]{status_val.upper()}[/{status_color}]")
    console.print(f"  Notebook: {job_data.get('notebook', 'unknown')}")

    if job_data.get("cell") is not None:
        console.print(f"  Cell: {job_data['cell']}")

    if job_data.get("started"):
        console.print(f"  Started: {job_data['started']}")

    if job_data.get("completed"):
        console.print(f"  Completed: {job_data['completed']}")

    if job_data.get("progress"):
        console.print(f"  Progress: {job_data['progress']}")

    if job_data.get("cells_completed") is not None:
        console.print(f"  Cells: {job_data['cells_completed']}/{job_data.get('cells_total', '?')}")

    if job_data.get("current_cell") is not None:
        console.print(f"  Current cell: {job_data['current_cell']}")

    if job_data.get("error"):
        console.print(f"  [red]Error: {job_data['error']}[/red]")

    if job_data.get("summary"):
        summary = job_data["summary"]
        console.print(f"\n  [bold]Summary:[/bold]")
        console.print(f"    Total: {summary.get('total', 0)}")
        console.print(f"    Succeeded: {summary.get('succeeded', 0)}")
        console.print(f"    Failed: {summary.get('failed', 0)}")

    # Show log file location
    log_file = jobs_dir / f"{job_id}.log"
    if log_file.exists():
        console.print(f"\n  [dim]Log: {log_file}[/dim]")


def _watch_job(job_id: str, jobs_dir: Path) -> None:
    """Watch job status with live updates."""
    import time

    job_file = jobs_dir / f"{job_id}.json"

    console.print(f"Watching job {job_id}... (Ctrl+C to stop)\n")

    last_progress = None

    try:
        while True:
            if not job_file.exists():
                console.print("[red]Job file not found[/red]")
                break

            job_data = json.loads(job_file.read_text())
            status_val = job_data.get("status", "unknown")
            progress = job_data.get("progress", "")

            if progress != last_progress:
                status_color = {
                    "running": "yellow",
                    "completed": "green",
                    "failed": "red"
                }.get(status_val, "white")

                console.print(
                    f"[{status_color}]{status_val.upper()}[/{status_color}] "
                    f"Progress: {progress} "
                    f"Cell: {job_data.get('current_cell', '-')}"
                )
                last_progress = progress

            if status_val in ["completed", "failed", "cancelled"]:
                console.print(f"\n[bold]Job finished with status: {status_val}[/bold]")
                break

            time.sleep(1)

    except KeyboardInterrupt:
        console.print("\n[dim]Stopped watching[/dim]")

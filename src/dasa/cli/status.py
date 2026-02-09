"""Status command — check background job progress."""

import json
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from dasa.session.jobs import JobManager

console = Console()


def status(
    job_id: Optional[str] = typer.Argument(None, help="Job ID to check (omit for all jobs)"),
    format: str = typer.Option("text", "--format", "-f", help="Output format: text, json"),
) -> None:
    """Check status of background execution jobs."""
    mgr = JobManager()

    if job_id:
        job = mgr.get_job(job_id)
        if job is None:
            console.print(f"[red]Job {job_id} not found[/red]")
            raise typer.Exit(1)

        # Check if process is actually still running
        if job.status == "running" and not mgr.is_running(job_id):
            job = mgr.update_job(job_id, status="failed", error="Process terminated unexpectedly")

        if format == "json":
            from dataclasses import asdict
            console.print(json.dumps(asdict(job), indent=2))
        else:
            _print_job(job)
    else:
        jobs = mgr.list_jobs()
        if not jobs:
            console.print("[dim]No jobs found.[/dim]")
            return

        # Update status of running jobs
        for job in jobs:
            if job.status == "running" and not mgr.is_running(job.id):
                mgr.update_job(job.id, status="failed", error="Process terminated unexpectedly")

        if format == "json":
            from dataclasses import asdict
            console.print(json.dumps([asdict(j) for j in jobs], indent=2))
        else:
            _print_job_table(jobs)


def _print_job(job) -> None:
    """Print a single job's details."""
    status_color = {"running": "yellow", "completed": "green", "failed": "red"}.get(job.status, "white")
    console.print(f"[bold]Job {job.id}[/bold]")
    console.print(f"  Notebook: {job.notebook}")
    console.print(f"  Cell: {job.cell}")
    console.print(f"  Status: [{status_color}]{job.status.upper()}[/{status_color}]")
    console.print(f"  Started: {job.started_at}")
    if job.completed_at:
        console.print(f"  Completed: {job.completed_at}")
    if job.error:
        console.print(f"  Error: [red]{job.error}[/red]")
    if job.result:
        console.print(f"  Result: {json.dumps(job.result, indent=2)}")


def _print_job_table(jobs) -> None:
    """Print a table of all jobs."""
    table = Table(title="Background Jobs")
    table.add_column("ID", style="cyan")
    table.add_column("Notebook")
    table.add_column("Cell")
    table.add_column("Status")
    table.add_column("Started")

    for job in jobs:
        status_color = {"running": "yellow", "completed": "green", "failed": "red"}.get(job.status, "white")
        table.add_row(
            job.id,
            job.notebook,
            str(job.cell),
            f"[{status_color}]{job.status.upper()}[/{status_color}]",
            job.started_at,
        )
    console.print(table)

"""Cancel command for async jobs."""

import json
import os
import signal
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from dasa.cli.status import get_jobs_dir

console = Console()


def cancel(
    job_id: str = typer.Argument(..., help="Job ID to cancel"),
) -> None:
    """Cancel a running async job."""

    jobs_dir = get_jobs_dir()
    job_file = jobs_dir / f"{job_id}.json"

    if not job_file.exists():
        console.print(f"[red]Job {job_id} not found[/red]")
        raise typer.Exit(1)

    job_data = json.loads(job_file.read_text())

    if job_data.get("status") != "running":
        console.print(f"[yellow]Job {job_id} is not running (status: {job_data.get('status')})[/yellow]")
        return

    pid = job_data.get("pid")

    if not pid:
        console.print("[red]No PID found for job[/red]")
        raise typer.Exit(1)

    try:
        # Send interrupt signal
        os.kill(pid, signal.SIGINT)
        console.print(f"[yellow]Sent interrupt to job {job_id} (PID {pid})[/yellow]")

        # Update job status
        job_data["status"] = "cancelled"
        job_file.write_text(json.dumps(job_data, indent=2))

        console.print(f"[green]Job {job_id} cancelled[/green]")

    except ProcessLookupError:
        console.print(f"[yellow]Process {pid} not found (may have already finished)[/yellow]")
        job_data["status"] = "cancelled"
        job_file.write_text(json.dumps(job_data, indent=2))

    except PermissionError:
        console.print(f"[red]Permission denied to cancel process {pid}[/red]")
        raise typer.Exit(1)

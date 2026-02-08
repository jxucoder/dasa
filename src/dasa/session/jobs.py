"""Async job tracking for background execution."""

import json
import os
import signal
import subprocess
import sys
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class Job:
    """Represents a background execution job."""
    id: str
    notebook: str
    cell: int
    pid: int
    status: str  # "running", "completed", "failed"
    started_at: str
    completed_at: Optional[str] = None
    result: Optional[dict] = None
    error: Optional[str] = None


class JobManager:
    """Manage background execution jobs."""

    def __init__(self, project_dir: str = "."):
        self.jobs_dir = Path(project_dir) / ".dasa" / "jobs"

    def create_job(self, notebook: str, cell: int) -> Job:
        """Create a new job record."""
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        job_id = uuid.uuid4().hex[:8]
        job = Job(
            id=job_id,
            notebook=notebook,
            cell=cell,
            pid=0,  # Will be set when process starts
            status="running",
            started_at=datetime.now().isoformat(),
        )
        self._save(job)
        return job

    def update_job(self, job_id: str, **kwargs) -> Optional[Job]:
        """Update a job's fields."""
        job = self.get_job(job_id)
        if job is None:
            return None
        for key, value in kwargs.items():
            if hasattr(job, key):
                setattr(job, key, value)
        self._save(job)
        return job

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by ID."""
        path = self.jobs_dir / f"{job_id}.json"
        if not path.exists():
            return None
        with open(path) as f:
            data = json.load(f)
        return Job(**data)

    def list_jobs(self, status: Optional[str] = None) -> list[Job]:
        """List all jobs, optionally filtered by status."""
        if not self.jobs_dir.exists():
            return []
        jobs = []
        for path in sorted(self.jobs_dir.glob("*.json")):
            with open(path) as f:
                data = json.load(f)
            job = Job(**data)
            if status is None or job.status == status:
                jobs.append(job)
        return jobs

    def is_running(self, job_id: str) -> bool:
        """Check if a job's process is still running."""
        job = self.get_job(job_id)
        if job is None or job.pid == 0:
            return False
        try:
            os.kill(job.pid, 0)
            return True
        except (ProcessLookupError, PermissionError):
            return False

    def _save(self, job: Job) -> None:
        """Save job to disk."""
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        path = self.jobs_dir / f"{job.id}.json"
        with open(path, "w") as f:
            json.dump(asdict(job), f, indent=2)

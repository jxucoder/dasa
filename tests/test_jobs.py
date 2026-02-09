"""Tests for job tracking."""

import tempfile
from pathlib import Path

from dasa.session.jobs import JobManager, Job


class TestJobManager:
    def test_create_job(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = JobManager(tmpdir)
            job = mgr.create_job("test.ipynb", 5)
            assert job.notebook == "test.ipynb"
            assert job.cell == 5
            assert job.status == "running"
            assert len(job.id) == 8

    def test_get_job(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = JobManager(tmpdir)
            job = mgr.create_job("test.ipynb", 3)
            retrieved = mgr.get_job(job.id)
            assert retrieved is not None
            assert retrieved.notebook == "test.ipynb"

    def test_update_job(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = JobManager(tmpdir)
            job = mgr.create_job("test.ipynb", 0)
            mgr.update_job(job.id, status="completed", completed_at="2026-02-08T12:00:00")
            updated = mgr.get_job(job.id)
            assert updated.status == "completed"
            assert updated.completed_at == "2026-02-08T12:00:00"

    def test_list_jobs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = JobManager(tmpdir)
            mgr.create_job("a.ipynb", 0)
            mgr.create_job("b.ipynb", 1)
            jobs = mgr.list_jobs()
            assert len(jobs) == 2

    def test_list_jobs_filtered(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = JobManager(tmpdir)
            j1 = mgr.create_job("a.ipynb", 0)
            j2 = mgr.create_job("b.ipynb", 1)
            mgr.update_job(j1.id, status="completed")
            running = mgr.list_jobs(status="running")
            assert len(running) == 1
            assert running[0].id == j2.id

    def test_get_nonexistent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = JobManager(tmpdir)
            assert mgr.get_job("nonexistent") is None

    def test_list_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = JobManager(tmpdir)
            assert mgr.list_jobs() == []

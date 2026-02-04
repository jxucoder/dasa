"""Tests for result command."""

import json
import pytest
from pathlib import Path
from typer.testing import CliRunner
from dasa.cli.main import app


runner = CliRunner()


def test_result_help():
    """Test result command help."""
    result = runner.invoke(app, ["result", "--help"])
    assert result.exit_code == 0
    assert "job" in result.stdout.lower() or "result" in result.stdout.lower()


def test_result_requires_job_id():
    """Test result requires job ID argument."""
    result = runner.invoke(app, ["result"])
    assert result.exit_code != 0


def test_result_job_not_found():
    """Test result for non-existent job."""
    result = runner.invoke(app, ["result", "nonexistent-job-id"])
    assert result.exit_code != 0
    assert "not found" in result.stdout.lower()


def test_result_completed_job(tmp_path, monkeypatch):
    """Test result for a completed job."""
    # Create a mock jobs directory
    jobs_dir = tmp_path / ".dasa" / "jobs"
    jobs_dir.mkdir(parents=True)

    # Create a completed job file
    job_data = {
        "id": "test-job-123",
        "status": "completed",
        "notebook": "/path/to/test.ipynb",
        "results": [
            {"cell": 0, "success": True, "stdout": "Hello World\n", "elapsed": 0.5},
            {"cell": 1, "success": True, "stdout": "42\n", "elapsed": 0.3}
        ],
        "summary": {"total": 2, "succeeded": 2, "failed": 0}
    }
    job_file = jobs_dir / "test-job-123.json"
    job_file.write_text(json.dumps(job_data))

    # Monkeypatch the jobs directory
    from dasa.cli import result as result_module
    monkeypatch.setattr(result_module, "get_jobs_dir", lambda: jobs_dir)

    result = runner.invoke(app, ["result", "test-job-123"])
    assert result.exit_code == 0
    assert "completed" in result.stdout.lower()


def test_result_running_job(tmp_path, monkeypatch):
    """Test result for a running job."""
    jobs_dir = tmp_path / ".dasa" / "jobs"
    jobs_dir.mkdir(parents=True)

    job_data = {
        "id": "running-job",
        "status": "running",
        "progress": "50%",
        "current_cell": 3
    }
    job_file = jobs_dir / "running-job.json"
    job_file.write_text(json.dumps(job_data))

    from dasa.cli import result as result_module
    monkeypatch.setattr(result_module, "get_jobs_dir", lambda: jobs_dir)

    result = runner.invoke(app, ["result", "running-job"])
    assert result.exit_code == 2  # Still running
    assert "still running" in result.stdout.lower()


def test_result_json_format(tmp_path, monkeypatch):
    """Test result with JSON output format."""
    jobs_dir = tmp_path / ".dasa" / "jobs"
    jobs_dir.mkdir(parents=True)

    job_data = {
        "id": "json-job",
        "status": "completed",
        "results": [{"cell": 0, "success": True}],
        "summary": {"total": 1, "succeeded": 1, "failed": 0}
    }
    job_file = jobs_dir / "json-job.json"
    job_file.write_text(json.dumps(job_data))

    from dasa.cli import result as result_module
    monkeypatch.setattr(result_module, "get_jobs_dir", lambda: jobs_dir)

    result = runner.invoke(app, ["result", "json-job", "--format", "json"])
    assert result.exit_code == 0
    output = json.loads(result.stdout)
    assert output["status"] == "completed"


def test_result_specific_cell(tmp_path, monkeypatch):
    """Test result for specific cell."""
    jobs_dir = tmp_path / ".dasa" / "jobs"
    jobs_dir.mkdir(parents=True)

    job_data = {
        "id": "cell-job",
        "status": "completed",
        "results": [
            {"cell": 0, "success": True, "stdout": "first"},
            {"cell": 1, "success": True, "stdout": "second"}
        ],
        "summary": {"total": 2, "succeeded": 2, "failed": 0}
    }
    job_file = jobs_dir / "cell-job.json"
    job_file.write_text(json.dumps(job_data))

    from dasa.cli import result as result_module
    monkeypatch.setattr(result_module, "get_jobs_dir", lambda: jobs_dir)

    result = runner.invoke(app, ["result", "cell-job", "--cell", "1"])
    assert result.exit_code == 0

"""Tests for status command."""

import json
import pytest
from typer.testing import CliRunner
from dasa.cli.main import app


runner = CliRunner()


def test_status_help():
    """Test status command help."""
    result = runner.invoke(app, ["status", "--help"])
    assert result.exit_code == 0
    assert "job" in result.stdout.lower() or "status" in result.stdout.lower()


def test_status_list_all_jobs():
    """Test status lists all jobs when no job_id provided."""
    result = runner.invoke(app, ["status"])
    # Should succeed and show jobs table or "No jobs found"
    assert result.exit_code == 0


def test_status_specific_job_not_found():
    """Test status for non-existent job."""
    result = runner.invoke(app, ["status", "nonexistent-job-id"])
    assert result.exit_code != 0 or "not found" in result.stdout.lower()


def test_status_json_format():
    """Test status with JSON output format."""
    result = runner.invoke(app, ["status", "--format", "json"])
    assert result.exit_code == 0

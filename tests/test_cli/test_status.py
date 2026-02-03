"""Tests for status command."""

import pytest
from typer.testing import CliRunner
from dasa.cli.main import app


runner = CliRunner()


def test_status_help():
    """Test status command help."""
    result = runner.invoke(app, ["status", "--help"])
    assert result.exit_code == 0
    assert "job" in result.stdout.lower() or "status" in result.stdout.lower()


def test_status_requires_job_id():
    """Test status requires job ID argument."""
    result = runner.invoke(app, ["status"])
    # Should fail without job_id
    assert result.exit_code != 0


def test_status_specific_job_not_found():
    """Test status for non-existent job."""
    result = runner.invoke(app, ["status", "nonexistent-job-id"])
    assert result.exit_code != 0 or "not found" in result.stdout.lower()

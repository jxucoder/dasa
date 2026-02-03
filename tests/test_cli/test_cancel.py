"""Tests for cancel command."""

import pytest
from typer.testing import CliRunner
from dasa.cli.main import app


runner = CliRunner()


def test_cancel_help():
    """Test cancel command help."""
    result = runner.invoke(app, ["cancel", "--help"])
    assert result.exit_code == 0
    assert "job" in result.stdout.lower() or "cancel" in result.stdout.lower()


def test_cancel_requires_job_id():
    """Test cancel command requires job ID."""
    result = runner.invoke(app, ["cancel"])
    assert result.exit_code != 0


def test_cancel_nonexistent_job():
    """Test cancel for non-existent job."""
    result = runner.invoke(app, ["cancel", "nonexistent-job-id"])
    assert result.exit_code != 0 or "not found" in result.stdout.lower()

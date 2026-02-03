"""Tests for stale command."""

import pytest
from typer.testing import CliRunner
from dasa.cli.main import app


runner = CliRunner()


def test_stale_help():
    """Test stale command help."""
    result = runner.invoke(app, ["stale", "--help"])
    assert result.exit_code == 0
    assert "stale" in result.stdout.lower() or "outdated" in result.stdout.lower()


def test_stale_requires_notebook():
    """Test stale command requires notebook argument."""
    result = runner.invoke(app, ["stale"])
    assert result.exit_code != 0


def test_stale_nonexistent_notebook():
    """Test stale with nonexistent notebook."""
    result = runner.invoke(app, ["stale", "nonexistent.ipynb"])
    assert result.exit_code != 0

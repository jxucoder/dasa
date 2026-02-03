"""Tests for CLI main module."""

import pytest
from typer.testing import CliRunner
from dasa.cli.main import app


runner = CliRunner()


def test_version():
    """Test version command."""
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "dasa" in result.stdout


def test_help():
    """Test help output."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Data Science Agent toolkit" in result.stdout


def test_profile_help():
    """Test profile command help."""
    result = runner.invoke(app, ["profile", "--help"])
    assert result.exit_code == 0
    assert "Profile a variable" in result.stdout


def test_validate_help():
    """Test validate command help."""
    result = runner.invoke(app, ["validate", "--help"])
    assert result.exit_code == 0
    assert "notebook state" in result.stdout


def test_deps_help():
    """Test deps command help."""
    result = runner.invoke(app, ["deps", "--help"])
    assert result.exit_code == 0
    assert "dependencies" in result.stdout


def test_run_help():
    """Test run command help."""
    result = runner.invoke(app, ["run", "--help"])
    assert result.exit_code == 0
    assert "Execute" in result.stdout


def test_replay_help():
    """Test replay command help."""
    result = runner.invoke(app, ["replay", "--help"])
    assert result.exit_code == 0
    assert "reproducibility" in result.stdout

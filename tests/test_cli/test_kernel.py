"""Tests for kernel command."""

import pytest
from typer.testing import CliRunner
from dasa.cli.main import app


runner = CliRunner()


def test_kernel_help():
    """Test kernel command help."""
    result = runner.invoke(app, ["kernel", "--help"])
    assert result.exit_code == 0
    assert "status" in result.stdout.lower() or "kernel" in result.stdout.lower()


def test_kernel_status_help():
    """Test kernel status subcommand help."""
    result = runner.invoke(app, ["kernel", "status", "--help"])
    assert result.exit_code == 0


def test_kernel_restart_help():
    """Test kernel restart subcommand help."""
    result = runner.invoke(app, ["kernel", "restart", "--help"])
    assert result.exit_code == 0


def test_kernel_interrupt_help():
    """Test kernel interrupt subcommand help."""
    result = runner.invoke(app, ["kernel", "interrupt", "--help"])
    assert result.exit_code == 0

"""Tests for mcp-serve command."""

import pytest
from typer.testing import CliRunner
from dasa.cli.main import app


runner = CliRunner()


def test_mcp_serve_help():
    """Test mcp-serve command help."""
    result = runner.invoke(app, ["mcp-serve", "--help"])
    assert result.exit_code == 0
    assert "mcp" in result.stdout.lower() or "server" in result.stdout.lower()


def test_mcp_serve_has_transport_option():
    """Test mcp-serve has transport option."""
    result = runner.invoke(app, ["mcp-serve", "--help"])
    assert result.exit_code == 0
    assert "transport" in result.stdout.lower()

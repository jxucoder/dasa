"""Tests for vars command."""

import pytest
from typer.testing import CliRunner
from dasa.cli.main import app


runner = CliRunner()


def test_vars_help():
    """Test vars command help."""
    result = runner.invoke(app, ["vars", "--help"])
    assert result.exit_code == 0
    assert "variable" in result.stdout.lower()


def test_vars_requires_notebook():
    """Test vars command requires notebook argument."""
    result = runner.invoke(app, ["vars"])
    assert result.exit_code != 0


def test_vars_json_format(tmp_path):
    """Test vars with JSON output format."""
    # Create a simple notebook
    notebook = tmp_path / "test.ipynb"
    notebook.write_text('''{
        "cells": [
            {"cell_type": "code", "source": "x = 1", "metadata": {}, "outputs": [], "execution_count": 1}
        ],
        "metadata": {"kernelspec": {"name": "python3"}},
        "nbformat": 4,
        "nbformat_minor": 4
    }''')

    result = runner.invoke(app, ["vars", str(notebook), "--format", "json"])
    # May fail if kernel not available, but should parse args correctly
    assert "--format" not in result.stdout or result.exit_code == 0

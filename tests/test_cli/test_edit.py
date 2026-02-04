"""Tests for edit command."""

import json
import pytest
from typer.testing import CliRunner
from dasa.cli.main import app


runner = CliRunner()


def test_edit_help():
    """Test edit command help."""
    result = runner.invoke(app, ["edit", "--help"])
    assert result.exit_code == 0
    assert "cell" in result.stdout.lower()


def test_edit_requires_notebook():
    """Test edit command requires notebook argument."""
    result = runner.invoke(app, ["edit", "--cell", "0", "--code", "x = 1"])
    assert result.exit_code != 0


def test_edit_requires_cell():
    """Test edit command requires cell option."""
    result = runner.invoke(app, ["edit", "test.ipynb", "--code", "x = 1"])
    assert result.exit_code != 0


def test_edit_cell(tmp_path):
    """Test editing a cell."""
    notebook = tmp_path / "test.ipynb"
    notebook.write_text(json.dumps({
        "cells": [
            {"cell_type": "code", "source": "x = 1", "metadata": {}, "outputs": [], "execution_count": 1}
        ],
        "metadata": {"kernelspec": {"name": "python3"}},
        "nbformat": 4,
        "nbformat_minor": 4
    }))

    result = runner.invoke(app, ["edit", str(notebook), "--cell", "0", "--code", "x = 42"])
    assert result.exit_code == 0

    data = json.loads(notebook.read_text())
    assert "x = 42" in data["cells"][0]["source"]


def test_edit_nonexistent_cell(tmp_path):
    """Test editing a nonexistent cell."""
    notebook = tmp_path / "test.ipynb"
    notebook.write_text(json.dumps({
        "cells": [
            {"cell_type": "code", "source": "x = 1", "metadata": {}, "outputs": [], "execution_count": 1}
        ],
        "metadata": {"kernelspec": {"name": "python3"}},
        "nbformat": 4,
        "nbformat_minor": 4
    }))

    result = runner.invoke(app, ["edit", str(notebook), "--cell", "99", "--code", "x = 42"])
    assert result.exit_code != 0

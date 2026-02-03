"""Tests for add command."""

import json
import pytest
from typer.testing import CliRunner
from dasa.cli.main import app


runner = CliRunner()


def test_add_help():
    """Test add command help."""
    result = runner.invoke(app, ["add", "--help"])
    assert result.exit_code == 0
    assert "cell" in result.stdout.lower()


def test_add_requires_notebook():
    """Test add command requires notebook argument."""
    result = runner.invoke(app, ["add", "--code", "x = 1"])
    assert result.exit_code != 0


def test_add_requires_code():
    """Test add command requires code option."""
    result = runner.invoke(app, ["add", "test.ipynb"])
    assert result.exit_code != 0


def test_add_cell(tmp_path):
    """Test adding a cell to a notebook."""
    notebook = tmp_path / "test.ipynb"
    notebook.write_text(json.dumps({
        "cells": [
            {"cell_type": "code", "source": "x = 1", "metadata": {}, "outputs": [], "execution_count": 1}
        ],
        "metadata": {"kernelspec": {"name": "python3"}},
        "nbformat": 4,
        "nbformat_minor": 4
    }))

    result = runner.invoke(app, ["add", str(notebook), "--code", "y = 2"])
    assert result.exit_code == 0

    # Verify cell was added
    data = json.loads(notebook.read_text())
    assert len(data["cells"]) == 2
    assert "y = 2" in data["cells"][-1]["source"]


def test_add_cell_at_position(tmp_path):
    """Test adding a cell at specific position."""
    notebook = tmp_path / "test.ipynb"
    notebook.write_text(json.dumps({
        "cells": [
            {"cell_type": "code", "source": "x = 1", "metadata": {}, "outputs": [], "execution_count": 1},
            {"cell_type": "code", "source": "z = 3", "metadata": {}, "outputs": [], "execution_count": 2}
        ],
        "metadata": {"kernelspec": {"name": "python3"}},
        "nbformat": 4,
        "nbformat_minor": 4
    }))

    result = runner.invoke(app, ["add", str(notebook), "--code", "y = 2", "--after", "0"])
    assert result.exit_code == 0

    data = json.loads(notebook.read_text())
    assert len(data["cells"]) == 3
    assert "y = 2" in data["cells"][1]["source"]


def test_add_markdown_cell(tmp_path):
    """Test adding a markdown cell."""
    notebook = tmp_path / "test.ipynb"
    notebook.write_text(json.dumps({
        "cells": [],
        "metadata": {"kernelspec": {"name": "python3"}},
        "nbformat": 4,
        "nbformat_minor": 4
    }))

    result = runner.invoke(app, ["add", str(notebook), "--markdown", "# Header"])
    assert result.exit_code == 0

    data = json.loads(notebook.read_text())
    assert len(data["cells"]) == 1
    assert data["cells"][0]["cell_type"] == "markdown"

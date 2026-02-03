"""Tests for move command."""

import json
import pytest
from typer.testing import CliRunner
from dasa.cli.main import app


runner = CliRunner()


def test_move_help():
    """Test move command help."""
    result = runner.invoke(app, ["move", "--help"])
    assert result.exit_code == 0
    assert "cell" in result.stdout.lower() or "move" in result.stdout.lower()


def test_move_requires_notebook():
    """Test move command requires notebook argument."""
    result = runner.invoke(app, ["move", "--cell", "0", "--to", "1"])
    assert result.exit_code != 0


def test_move_requires_cell():
    """Test move command requires cell option."""
    result = runner.invoke(app, ["move", "test.ipynb", "--to", "1"])
    assert result.exit_code != 0


def test_move_requires_to():
    """Test move command requires to option."""
    result = runner.invoke(app, ["move", "test.ipynb", "--cell", "0"])
    assert result.exit_code != 0


def test_move_cell_down(tmp_path):
    """Test moving a cell down."""
    notebook = tmp_path / "test.ipynb"
    notebook.write_text(json.dumps({
        "cells": [
            {"cell_type": "code", "source": "x = 1", "metadata": {}, "outputs": [], "execution_count": 1},
            {"cell_type": "code", "source": "y = 2", "metadata": {}, "outputs": [], "execution_count": 2},
            {"cell_type": "code", "source": "z = 3", "metadata": {}, "outputs": [], "execution_count": 3}
        ],
        "metadata": {"kernelspec": {"name": "python3"}},
        "nbformat": 4,
        "nbformat_minor": 4
    }))

    result = runner.invoke(app, ["move", str(notebook), "--cell", "0", "--to", "2", "--force"])
    assert result.exit_code == 0

    data = json.loads(notebook.read_text())
    assert len(data["cells"]) == 3
    # First cell should now be y = 2
    assert "y = 2" in data["cells"][0]["source"]


def test_move_cell_up(tmp_path):
    """Test moving a cell up."""
    notebook = tmp_path / "test.ipynb"
    notebook.write_text(json.dumps({
        "cells": [
            {"cell_type": "code", "source": "x = 1", "metadata": {}, "outputs": [], "execution_count": 1},
            {"cell_type": "code", "source": "y = 2", "metadata": {}, "outputs": [], "execution_count": 2},
            {"cell_type": "code", "source": "z = 3", "metadata": {}, "outputs": [], "execution_count": 3}
        ],
        "metadata": {"kernelspec": {"name": "python3"}},
        "nbformat": 4,
        "nbformat_minor": 4
    }))

    result = runner.invoke(app, ["move", str(notebook), "--cell", "2", "--to", "0", "--force"])
    assert result.exit_code == 0

    data = json.loads(notebook.read_text())
    assert len(data["cells"]) == 3
    # First cell should now be z = 3
    assert "z = 3" in data["cells"][0]["source"]


def test_move_nonexistent_cell(tmp_path):
    """Test moving a nonexistent cell."""
    notebook = tmp_path / "test.ipynb"
    notebook.write_text(json.dumps({
        "cells": [
            {"cell_type": "code", "source": "x = 1", "metadata": {}, "outputs": [], "execution_count": 1}
        ],
        "metadata": {"kernelspec": {"name": "python3"}},
        "nbformat": 4,
        "nbformat_minor": 4
    }))

    result = runner.invoke(app, ["move", str(notebook), "--cell", "99", "--to", "0", "--force"])
    assert result.exit_code != 0

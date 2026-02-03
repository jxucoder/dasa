"""Tests for delete command."""

import json
import pytest
from typer.testing import CliRunner
from dasa.cli.main import app


runner = CliRunner()


def test_delete_help():
    """Test delete command help."""
    result = runner.invoke(app, ["delete", "--help"])
    assert result.exit_code == 0
    assert "cell" in result.stdout.lower() or "delete" in result.stdout.lower()


def test_delete_requires_notebook():
    """Test delete command requires notebook argument."""
    result = runner.invoke(app, ["delete", "--cell", "0"])
    assert result.exit_code != 0


def test_delete_requires_cell():
    """Test delete command requires cell option."""
    result = runner.invoke(app, ["delete", "test.ipynb"])
    assert result.exit_code != 0


def test_delete_cell(tmp_path):
    """Test deleting a cell."""
    notebook = tmp_path / "test.ipynb"
    notebook.write_text(json.dumps({
        "cells": [
            {"cell_type": "code", "source": "x = 1", "metadata": {}, "outputs": [], "execution_count": 1},
            {"cell_type": "code", "source": "y = 2", "metadata": {}, "outputs": [], "execution_count": 2}
        ],
        "metadata": {"kernelspec": {"name": "python3"}},
        "nbformat": 4,
        "nbformat_minor": 4
    }))

    result = runner.invoke(app, ["delete", str(notebook), "--cell", "0", "--force"])
    assert result.exit_code == 0

    data = json.loads(notebook.read_text())
    assert len(data["cells"]) == 1
    assert "y = 2" in data["cells"][0]["source"]


def test_delete_nonexistent_cell(tmp_path):
    """Test deleting a nonexistent cell."""
    notebook = tmp_path / "test.ipynb"
    notebook.write_text(json.dumps({
        "cells": [
            {"cell_type": "code", "source": "x = 1", "metadata": {}, "outputs": [], "execution_count": 1}
        ],
        "metadata": {"kernelspec": {"name": "python3"}},
        "nbformat": 4,
        "nbformat_minor": 4
    }))

    result = runner.invoke(app, ["delete", str(notebook), "--cell", "99", "--force"])
    assert result.exit_code != 0

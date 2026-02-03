"""Tests for cells command."""

import json
import pytest
from typer.testing import CliRunner
from dasa.cli.main import app


runner = CliRunner()


def test_cells_help():
    """Test cells command help."""
    result = runner.invoke(app, ["cells", "--help"])
    assert result.exit_code == 0
    assert "cell" in result.stdout.lower()


def test_cells_requires_notebook():
    """Test cells command requires notebook argument."""
    result = runner.invoke(app, ["cells"])
    assert result.exit_code != 0


def test_cells_basic(tmp_path):
    """Test cells command with basic notebook."""
    notebook = tmp_path / "test.ipynb"
    notebook.write_text(json.dumps({
        "cells": [
            {"cell_type": "code", "source": "x = 1", "metadata": {}, "outputs": [], "execution_count": 1},
            {"cell_type": "markdown", "source": "# Header", "metadata": {}},
            {"cell_type": "code", "source": "y = 2", "metadata": {}, "outputs": [], "execution_count": 2}
        ],
        "metadata": {"kernelspec": {"name": "python3"}},
        "nbformat": 4,
        "nbformat_minor": 4
    }))

    result = runner.invoke(app, ["cells", str(notebook)])
    assert result.exit_code == 0
    assert "x = 1" in result.stdout or "code" in result.stdout.lower()


def test_cells_json_format(tmp_path):
    """Test cells with JSON output format."""
    notebook = tmp_path / "test.ipynb"
    notebook.write_text(json.dumps({
        "cells": [
            {"cell_type": "code", "source": "x = 1", "metadata": {}, "outputs": [], "execution_count": 1}
        ],
        "metadata": {"kernelspec": {"name": "python3"}},
        "nbformat": 4,
        "nbformat_minor": 4
    }))

    result = runner.invoke(app, ["cells", str(notebook), "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert isinstance(data, list) or "cells" in data

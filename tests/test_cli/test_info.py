"""Tests for info command."""

import json
import pytest
from typer.testing import CliRunner
from dasa.cli.main import app


runner = CliRunner()


def test_info_help():
    """Test info command help."""
    result = runner.invoke(app, ["info", "--help"])
    assert result.exit_code == 0
    assert "notebook" in result.stdout.lower() or "info" in result.stdout.lower()


def test_info_requires_notebook():
    """Test info command requires notebook argument."""
    result = runner.invoke(app, ["info"])
    assert result.exit_code != 0


def test_info_basic(tmp_path):
    """Test info command with basic notebook."""
    notebook = tmp_path / "test.ipynb"
    notebook.write_text(json.dumps({
        "cells": [
            {"cell_type": "code", "source": "import pandas as pd", "metadata": {}, "outputs": [], "execution_count": 1},
            {"cell_type": "markdown", "source": "# Header", "metadata": {}},
            {"cell_type": "code", "source": "x = 1", "metadata": {}, "outputs": [], "execution_count": 2}
        ],
        "metadata": {
            "kernelspec": {"name": "python3", "display_name": "Python 3"},
            "language_info": {"name": "python", "version": "3.10.0"}
        },
        "nbformat": 4,
        "nbformat_minor": 4
    }))

    result = runner.invoke(app, ["info", str(notebook)])
    assert result.exit_code == 0
    assert "python" in result.stdout.lower() or "cell" in result.stdout.lower()


def test_info_json_format(tmp_path):
    """Test info with JSON output format."""
    notebook = tmp_path / "test.ipynb"
    notebook.write_text(json.dumps({
        "cells": [
            {"cell_type": "code", "source": "x = 1", "metadata": {}, "outputs": [], "execution_count": 1}
        ],
        "metadata": {"kernelspec": {"name": "python3"}},
        "nbformat": 4,
        "nbformat_minor": 4
    }))

    result = runner.invoke(app, ["info", str(notebook), "--format", "json"])
    assert result.exit_code == 0
    # Should be valid JSON
    data = json.loads(result.stdout)
    assert "cells" in data or "kernel" in data

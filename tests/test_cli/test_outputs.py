"""Tests for outputs command."""

import json
import pytest
from typer.testing import CliRunner
from dasa.cli.main import app


runner = CliRunner()


def test_outputs_help():
    """Test outputs command help."""
    result = runner.invoke(app, ["outputs", "--help"])
    assert result.exit_code == 0
    assert "output" in result.stdout.lower()


def test_outputs_requires_notebook():
    """Test outputs command requires notebook argument."""
    result = runner.invoke(app, ["outputs"])
    assert result.exit_code != 0


def test_outputs_basic(tmp_path):
    """Test outputs command with notebook containing outputs."""
    notebook = tmp_path / "test.ipynb"
    notebook.write_text(json.dumps({
        "cells": [
            {
                "cell_type": "code",
                "source": "print('hello')",
                "metadata": {},
                "outputs": [
                    {"output_type": "stream", "name": "stdout", "text": "hello\n"}
                ],
                "execution_count": 1
            }
        ],
        "metadata": {"kernelspec": {"name": "python3"}},
        "nbformat": 4,
        "nbformat_minor": 4
    }))

    result = runner.invoke(app, ["outputs", str(notebook), "--cell", "0"])
    assert result.exit_code == 0


def test_outputs_specific_cell(tmp_path):
    """Test outputs for specific cell."""
    notebook = tmp_path / "test.ipynb"
    notebook.write_text(json.dumps({
        "cells": [
            {
                "cell_type": "code",
                "source": "x = 1",
                "metadata": {},
                "outputs": [],
                "execution_count": 1
            },
            {
                "cell_type": "code",
                "source": "print('hello')",
                "metadata": {},
                "outputs": [
                    {"output_type": "stream", "name": "stdout", "text": "hello\n"}
                ],
                "execution_count": 2
            }
        ],
        "metadata": {"kernelspec": {"name": "python3"}},
        "nbformat": 4,
        "nbformat_minor": 4
    }))

    result = runner.invoke(app, ["outputs", str(notebook), "--cell", "1"])
    assert result.exit_code == 0

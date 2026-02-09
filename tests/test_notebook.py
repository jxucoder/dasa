"""Tests for notebook adapter."""

import json
import tempfile
from pathlib import Path

from dasa.notebook.jupyter import JupyterAdapter


def _create_test_notebook(path: str, cells: list[dict]) -> None:
    """Create a minimal valid notebook file."""
    nb = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3"
            },
            "language_info": {"name": "python", "version": "3.10.0"}
        },
        "cells": []
    }
    for cell_data in cells:
        cell = {
            "cell_type": cell_data.get("cell_type", "code"),
            "source": cell_data.get("source", ""),
            "metadata": {},
            "outputs": cell_data.get("outputs", []),
        }
        if cell["cell_type"] == "code":
            cell["execution_count"] = cell_data.get("execution_count")
        nb["cells"].append(cell)
    with open(path, "w") as f:
        json.dump(nb, f)


class TestJupyterAdapter:
    def test_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = f"{tmpdir}/test.ipynb"
            _create_test_notebook(path, [
                {"source": "x = 1", "execution_count": 1},
                {"source": "print(x)", "execution_count": 2},
            ])
            adapter = JupyterAdapter(path)
            assert len(adapter.cells) == 2
            assert adapter.cells[0].source == "x = 1"

    def test_code_cells(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = f"{tmpdir}/test.ipynb"
            _create_test_notebook(path, [
                {"source": "x = 1", "execution_count": 1},
                {"source": "# comment", "cell_type": "markdown"},
                {"source": "print(x)", "execution_count": 2},
            ])
            adapter = JupyterAdapter(path)
            assert len(adapter.code_cells) == 2

    def test_execution_order(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = f"{tmpdir}/test.ipynb"
            _create_test_notebook(path, [
                {"source": "a = 1", "execution_count": 2},
                {"source": "b = 2", "execution_count": 1},
            ])
            adapter = JupyterAdapter(path)
            order = adapter.execution_order
            assert order == [1, 0]  # cell 1 executed first

    def test_update_cell(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = f"{tmpdir}/test.ipynb"
            _create_test_notebook(path, [
                {"source": "x = 1", "execution_count": 1},
            ])
            adapter = JupyterAdapter(path)
            adapter.update_cell(0, "x = 2")
            assert adapter.get_cell(0).source == "x = 2"

    def test_save(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = f"{tmpdir}/test.ipynb"
            _create_test_notebook(path, [
                {"source": "x = 1", "execution_count": 1},
            ])
            adapter = JupyterAdapter(path)
            adapter.update_cell(0, "x = 2")
            adapter.save()
            # Reload and verify
            adapter2 = JupyterAdapter(path)
            assert adapter2.get_cell(0).source == "x = 2"

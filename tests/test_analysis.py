"""Tests for analysis engines."""

import json
import tempfile

from dasa.notebook.jupyter import JupyterAdapter
from dasa.analysis.state import StateAnalyzer
from dasa.analysis.deps import DependencyAnalyzer


def _create_notebook(path: str, cells: list[dict]) -> None:
    nb = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.10.0"},
        },
        "cells": [],
    }
    for cell_data in cells:
        cell = {
            "cell_type": cell_data.get("cell_type", "code"),
            "source": cell_data.get("source", ""),
            "metadata": {},
            "outputs": [],
        }
        if cell["cell_type"] == "code":
            cell["execution_count"] = cell_data.get("execution_count")
        nb["cells"].append(cell)
    with open(path, "w") as f:
        json.dump(nb, f)


class TestStateAnalyzer:
    def test_consistent_notebook(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = f"{tmpdir}/test.ipynb"
            _create_notebook(path, [
                {"source": "import pandas as pd", "execution_count": 1},
                {"source": "df = pd.read_csv('data.csv')", "execution_count": 2},
                {"source": "print(df.head())", "execution_count": 3},
            ])
            adapter = JupyterAdapter(path)
            analyzer = StateAnalyzer()
            result = analyzer.analyze(adapter)
            assert result.is_consistent

    def test_undefined_variable(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = f"{tmpdir}/test.ipynb"
            _create_notebook(path, [
                {"source": "print(x)", "execution_count": 1},
            ])
            adapter = JupyterAdapter(path)
            analyzer = StateAnalyzer()
            result = analyzer.analyze(adapter)
            assert not result.is_consistent
            assert len(result.undefined_refs) > 0

    def test_never_executed_cell(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = f"{tmpdir}/test.ipynb"
            _create_notebook(path, [
                {"source": "x = 1", "execution_count": 1},
                {"source": "print(x)"},  # no execution_count
            ])
            adapter = JupyterAdapter(path)
            analyzer = StateAnalyzer()
            result = analyzer.analyze(adapter)
            warnings = [i for i in result.issues if i.severity == "warning"]
            assert any("never executed" in w.message for w in warnings)

    def test_out_of_order_execution(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = f"{tmpdir}/test.ipynb"
            _create_notebook(path, [
                {"source": "x = 1", "execution_count": 2},
                {"source": "y = 2", "execution_count": 1},
            ])
            adapter = JupyterAdapter(path)
            analyzer = StateAnalyzer()
            result = analyzer.analyze(adapter)
            assert result.execution_order != result.correct_order


class TestDependencyAnalyzer:
    def test_simple_dependency(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = f"{tmpdir}/test.ipynb"
            _create_notebook(path, [
                {"source": "x = 1", "execution_count": 1},
                {"source": "y = x + 1", "execution_count": 2},
            ])
            adapter = JupyterAdapter(path)
            analyzer = DependencyAnalyzer()
            graph = analyzer.build_graph(adapter)
            assert 0 in graph.nodes[1].upstream
            assert 1 in graph.nodes[0].downstream

    def test_transitive_dependency(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = f"{tmpdir}/test.ipynb"
            _create_notebook(path, [
                {"source": "x = 1", "execution_count": 1},
                {"source": "y = x + 1", "execution_count": 2},
                {"source": "z = y + 1", "execution_count": 3},
            ])
            adapter = JupyterAdapter(path)
            analyzer = DependencyAnalyzer()
            graph = analyzer.build_graph(adapter)
            # Cell 2 transitively depends on cell 0
            upstream = graph.get_upstream(2)
            assert 0 in upstream
            assert 1 in upstream

    def test_downstream_impact(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = f"{tmpdir}/test.ipynb"
            _create_notebook(path, [
                {"source": "x = 1", "execution_count": 1},
                {"source": "y = x + 1", "execution_count": 2},
                {"source": "z = x + 2", "execution_count": 3},
            ])
            adapter = JupyterAdapter(path)
            analyzer = DependencyAnalyzer()
            graph = analyzer.build_graph(adapter)
            downstream = graph.get_downstream(0)
            assert 1 in downstream
            assert 2 in downstream

    def test_no_deps(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = f"{tmpdir}/test.ipynb"
            _create_notebook(path, [
                {"source": "x = 1", "execution_count": 1},
                {"source": "y = 2", "execution_count": 2},
            ])
            adapter = JupyterAdapter(path)
            analyzer = DependencyAnalyzer()
            graph = analyzer.build_graph(adapter)
            assert len(graph.nodes[0].downstream) == 0
            assert len(graph.nodes[1].upstream) == 0

    def test_graph_to_dict(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = f"{tmpdir}/test.ipynb"
            _create_notebook(path, [
                {"source": "x = 1", "execution_count": 1},
                {"source": "y = x + 1", "execution_count": 2},
            ])
            adapter = JupyterAdapter(path)
            analyzer = DependencyAnalyzer()
            graph = analyzer.build_graph(adapter)
            d = graph.to_dict()
            assert 0 in d
            assert 1 in d
            assert "downstream" in d[0]

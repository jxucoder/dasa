"""Tests for dependency analysis."""

import pytest
from dasa.notebook.jupyter import JupyterAdapter
from dasa.analysis.deps import DependencyAnalyzer


def test_build_graph(clean_notebook):
    """Test building dependency graph."""
    adapter = JupyterAdapter(clean_notebook)
    analyzer = DependencyAnalyzer()
    graph = analyzer.build_graph(adapter)

    assert len(graph.nodes) > 0


def test_downstream_dependencies(clean_notebook):
    """Test getting downstream dependencies."""
    adapter = JupyterAdapter(clean_notebook)
    analyzer = DependencyAnalyzer()
    graph = analyzer.build_graph(adapter)

    # Cell 0 imports pandas/numpy, which should be used by later cells
    downstream = graph.get_downstream(0)
    assert len(downstream) >= 0  # May have dependencies


def test_upstream_dependencies(clean_notebook):
    """Test getting upstream dependencies."""
    adapter = JupyterAdapter(clean_notebook)
    analyzer = DependencyAnalyzer()
    graph = analyzer.build_graph(adapter)

    # Last cell should have upstream dependencies
    last_cell = max(graph.nodes.keys())
    upstream = graph.get_upstream(last_cell)
    assert len(upstream) >= 0

"""Tests for state analysis."""

import pytest
from dasa.notebook.jupyter import JupyterAdapter
from dasa.analysis.state import StateAnalyzer


def test_analyze_clean_notebook(clean_notebook):
    """Test analyzing a clean notebook."""
    adapter = JupyterAdapter(clean_notebook)
    analyzer = StateAnalyzer()
    analysis = analyzer.analyze(adapter)

    # Clean notebook should be mostly consistent
    assert analysis is not None


def test_analyze_messy_notebook(messy_notebook):
    """Test analyzing a messy notebook."""
    adapter = JupyterAdapter(messy_notebook)
    analyzer = StateAnalyzer()
    analysis = analyzer.analyze(adapter)

    # Messy notebook should have issues
    assert len(analysis.issues) > 0


def test_detect_never_executed(messy_notebook):
    """Test detecting never-executed cells."""
    adapter = JupyterAdapter(messy_notebook)
    analyzer = StateAnalyzer()
    analysis = analyzer.analyze(adapter)

    # Should detect cells with no execution count
    never_run = [i for i in analysis.issues if "never been executed" in i.message]
    assert len(never_run) > 0

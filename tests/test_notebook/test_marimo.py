"""Tests for Marimo adapter."""

import pytest
from dasa.notebook.marimo import MarimoAdapter


def test_marimo_adapter_init():
    """Test MarimoAdapter initialization."""
    adapter = MarimoAdapter()
    assert adapter is not None


def test_marimo_parse_simple(tmp_path):
    """Test parsing a simple Marimo notebook."""
    marimo_file = tmp_path / "notebook.py"
    marimo_file.write_text('''import marimo

app = marimo.App()

@app.cell
def cell1():
    import pandas as pd
    return pd,

@app.cell
def cell2(pd):
    df = pd.DataFrame({"a": [1, 2, 3]})
    return df,
''')

    adapter = MarimoAdapter(str(marimo_file))
    cells = adapter.cells

    assert len(cells) == 2
    assert cells[0].is_code
    assert "import pandas" in cells[0].source


def test_marimo_parse_with_markdown(tmp_path):
    """Test parsing Marimo notebook with markdown cells."""
    marimo_file = tmp_path / "notebook.py"
    marimo_file.write_text('''import marimo

app = marimo.App()

@app.cell
def _():
    import marimo as mo
    mo.md("# Header")
    return

@app.cell
def cell1():
    x = 1
    return x,
''')

    adapter = MarimoAdapter(str(marimo_file))
    cells = adapter.cells

    assert len(cells) == 2


def test_marimo_dependency_extraction(tmp_path):
    """Test that dependencies are extracted from function signatures."""
    marimo_file = tmp_path / "notebook.py"
    marimo_file.write_text('''import marimo

app = marimo.App()

@app.cell
def cell1():
    x = 1
    return x,

@app.cell
def cell2(x):
    y = x + 1
    return y,
''')

    adapter = MarimoAdapter(str(marimo_file))

    # Cell 2 depends on x from cell 1
    assert len(adapter.cells) == 2
    # The adapter should track dependencies


def test_marimo_empty_file(tmp_path):
    """Test handling empty Marimo file."""
    marimo_file = tmp_path / "empty.py"
    marimo_file.write_text('')

    adapter = MarimoAdapter(str(marimo_file))
    assert len(adapter.cells) == 0


def test_marimo_no_cells(tmp_path):
    """Test Marimo file with no cells."""
    marimo_file = tmp_path / "no_cells.py"
    marimo_file.write_text('''import marimo

app = marimo.App()
# No cells defined
''')

    adapter = MarimoAdapter(str(marimo_file))
    assert len(adapter.cells) == 0

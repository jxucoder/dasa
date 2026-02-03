"""Tests for Jupyter adapter."""

import pytest
from dasa.notebook.jupyter import JupyterAdapter


def test_load_notebook(clean_notebook):
    """Test loading a notebook."""
    adapter = JupyterAdapter(clean_notebook)
    assert len(adapter.cells) == 6
    assert adapter.cells[0].is_code


def test_get_cell(clean_notebook):
    """Test getting a cell by index."""
    adapter = JupyterAdapter(clean_notebook)
    cell = adapter.get_cell(0)
    assert cell.is_code
    assert "import" in cell.source


def test_code_cells(clean_notebook):
    """Test getting code cells only."""
    adapter = JupyterAdapter(clean_notebook)
    code_cells = adapter.code_cells
    assert all(c.is_code for c in code_cells)


def test_cell_preview(clean_notebook):
    """Test cell preview."""
    adapter = JupyterAdapter(clean_notebook)
    cell = adapter.cells[0]
    assert cell.preview
    assert len(cell.preview) <= 53  # 50 chars + '...'

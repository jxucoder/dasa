"""Tests for Marimo adapter."""

import tempfile
from pathlib import Path

from dasa.notebook.marimo import MarimoAdapter


SAMPLE_MARIMO = '''import marimo

app = marimo.App()


@app.cell
def cell1():
    import pandas as pd
    df = pd.read_csv('data.csv')
    return df,


@app.cell
def cell2(df):
    clean_df = df.dropna()
    return clean_df,


@app.cell
def cell3(clean_df):
    print(clean_df.describe())
    return


if __name__ == "__main__":
    app.run()
'''


class TestMarimoAdapter:
    def test_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = f"{tmpdir}/notebook.py"
            Path(path).write_text(SAMPLE_MARIMO)
            adapter = MarimoAdapter(path)
            assert len(adapter.cells) == 3

    def test_cell_source(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = f"{tmpdir}/notebook.py"
            Path(path).write_text(SAMPLE_MARIMO)
            adapter = MarimoAdapter(path)
            # First cell should contain import and read_csv
            assert "pandas" in adapter.cells[0].source
            assert "read_csv" in adapter.cells[0].source

    def test_code_cells(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = f"{tmpdir}/notebook.py"
            Path(path).write_text(SAMPLE_MARIMO)
            adapter = MarimoAdapter(path)
            assert len(adapter.code_cells) == 3

    def test_save_raises(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = f"{tmpdir}/notebook.py"
            Path(path).write_text(SAMPLE_MARIMO)
            adapter = MarimoAdapter(path)
            try:
                adapter.save()
                assert False, "Should have raised NotImplementedError"
            except NotImplementedError:
                pass

    def test_empty_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = f"{tmpdir}/empty.py"
            Path(path).write_text("# no cells here\nprint('hello')\n")
            adapter = MarimoAdapter(path)
            assert len(adapter.cells) == 0


class TestMarimoAdapterNoCells:
    def test_no_decorator(self):
        source = '''import marimo
app = marimo.App()

def regular_function():
    return 42
'''
        with tempfile.TemporaryDirectory() as tmpdir:
            path = f"{tmpdir}/no_cells.py"
            Path(path).write_text(source)
            adapter = MarimoAdapter(path)
            assert len(adapter.cells) == 0

"""Tests for Sprint 6: Reliability & Cross-Command Integration."""

import json
import tempfile
from pathlib import Path

import nbformat

from dasa.session.state import StateTracker
from dasa.session.context import ContextManager
from dasa.session.profiles import ProfileCache
from dasa.analysis.state import StateAnalyzer
from dasa.notebook.jupyter import JupyterAdapter
from dasa.notebook.base import Cell

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_notebook(tmpdir: str, cells: list[tuple[str, int | None]]) -> str:
    """Create a minimal .ipynb with given code cells and execution counts."""
    nb = nbformat.v4.new_notebook()
    for source, exec_count in cells:
        cell = nbformat.v4.new_code_cell(source=source)
        cell["execution_count"] = exec_count
        nb.cells.append(cell)
    path = Path(tmpdir) / "test.ipynb"
    with open(path, "w") as f:
        nbformat.write(nb, f)
    return str(path)


# ---------------------------------------------------------------------------
# StateTracker: path normalization
# ---------------------------------------------------------------------------

class TestPathNormalization:
    def test_relative_paths_resolve_to_same_key(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = StateTracker(tmpdir)
            # Write with one relative path
            tracker.update_cell("./test.ipynb", 0, "x = 1")
            # Read with a different relative path
            assert not tracker.is_stale("test.ipynb", 0, "x = 1")

    def test_normalize_path_is_absolute(self):
        result = StateTracker._normalize_path("test.ipynb")
        assert Path(result).is_absolute()

    def test_normalize_path_consistent(self):
        a = StateTracker._normalize_path("./dir/../test.ipynb")
        b = StateTracker._normalize_path("test.ipynb")
        assert a == b


# ---------------------------------------------------------------------------
# StateTracker: new helper methods
# ---------------------------------------------------------------------------

class TestStateTrackerHelpers:
    def test_was_executed_true(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = StateTracker(tmpdir)
            tracker.update_cell("test.ipynb", 0, "x = 1")
            assert tracker.was_executed("test.ipynb", 0)

    def test_was_executed_false(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = StateTracker(tmpdir)
            assert not tracker.was_executed("test.ipynb", 0)

    def test_was_executed_current_true(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = StateTracker(tmpdir)
            tracker.update_cell("test.ipynb", 0, "x = 1")
            assert tracker.was_executed_current("test.ipynb", 0, "x = 1")

    def test_was_executed_current_false_when_stale(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = StateTracker(tmpdir)
            tracker.update_cell("test.ipynb", 0, "x = 1")
            # Code changed → not current
            assert not tracker.was_executed_current("test.ipynb", 0, "x = 2")

    def test_was_executed_current_false_when_never_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = StateTracker(tmpdir)
            assert not tracker.was_executed_current("test.ipynb", 0, "x = 1")


# ---------------------------------------------------------------------------
# StateTracker: atomic writes and robust I/O
# ---------------------------------------------------------------------------

class TestAtomicWritesAndRobustIO:
    def test_corrupted_state_json_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = Path(tmpdir) / ".dasa" / "state.json"
            state_path.parent.mkdir(parents=True)
            state_path.write_text("NOT VALID JSON {{{")

            tracker = StateTracker(tmpdir)
            # Should not raise — returns empty dict
            assert tracker.is_stale("test.ipynb", 0, "x = 1")

    def test_corrupted_context_yaml_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ctx_mgr = ContextManager(tmpdir)
            ctx_mgr.ensure_session()
            # Write corrupted YAML
            ctx_mgr.context_path.write_text(": : : invalid yaml [[[")

            ctx = ctx_mgr.read()
            assert ctx.goal is None
            assert ctx.name is None

    def test_corrupted_profile_returns_none(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ProfileCache(tmpdir)
            cache.profiles_dir.mkdir(parents=True)
            (cache.profiles_dir / "broken.yaml").write_text(": : invalid [[[")

            result = cache.load("broken")
            assert result is None

    def test_atomic_write_produces_valid_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = StateTracker(tmpdir)
            tracker.update_cell("test.ipynb", 0, "x = 1")
            tracker.update_cell("test.ipynb", 1, "y = 2")

            # Verify file is valid JSON
            with open(tracker.state_path) as f:
                data = json.load(f)
            assert isinstance(data, dict)


# ---------------------------------------------------------------------------
# StateAnalyzer: consults state.json
# ---------------------------------------------------------------------------

class TestStateAnalyzerWithStateJson:
    def test_cells_run_via_dasa_not_reported_as_never_executed(self):
        """The critical fix: check should not report 'never executed' for dasa-run cells."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create notebook with no execution_count (never run in Jupyter)
            nb_path = _make_notebook(tmpdir, [
                ("x = 1", None),
                ("y = x + 1", None),
            ])

            # Simulate dasa run having executed both cells
            tracker = StateTracker(tmpdir)
            tracker.update_cell(nb_path, 0, "x = 1")
            tracker.update_cell(nb_path, 1, "y = x + 1")

            # Analyze with notebook_path and tracker
            adapter = JupyterAdapter(nb_path)
            analyzer = StateAnalyzer()
            analysis = analyzer.analyze(
                adapter, notebook_path=nb_path, state_tracker=tracker
            )

            # Should NOT have "never executed" warnings
            never_executed = [
                i for i in analysis.issues if "never executed" in i.message
            ]
            assert len(never_executed) == 0

    def test_cells_not_run_anywhere_reported_as_never_executed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            nb_path = _make_notebook(tmpdir, [
                ("x = 1", None),
                ("y = x + 1", None),
            ])

            tracker = StateTracker(tmpdir)
            adapter = JupyterAdapter(nb_path)
            analyzer = StateAnalyzer()
            analysis = analyzer.analyze(
                adapter, notebook_path=nb_path, state_tracker=tracker
            )

            never_executed = [
                i for i in analysis.issues if "never executed" in i.message
            ]
            assert len(never_executed) == 2

    def test_stale_cells_detected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            nb_path = _make_notebook(tmpdir, [
                ("x = 1", None),  # Will be executed then changed
            ])

            # Execute via dasa
            tracker = StateTracker(tmpdir)
            tracker.update_cell(nb_path, 0, "x = 1")

            # Now change the cell source in the notebook
            adapter = JupyterAdapter(nb_path)
            adapter.update_cell(0, "x = 999")
            adapter.save()

            # Re-analyze
            adapter2 = JupyterAdapter(nb_path)
            analyzer = StateAnalyzer()
            analysis = analyzer.analyze(
                adapter2, notebook_path=nb_path, state_tracker=tracker
            )

            stale = [i for i in analysis.issues if "stale" in i.message]
            assert len(stale) == 1

    def test_backward_compat_no_notebook_path(self):
        """Without notebook_path, analyzer falls back to execution_count only."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nb_path = _make_notebook(tmpdir, [
                ("x = 1", None),
                ("y = x + 1", 1),
            ])

            adapter = JupyterAdapter(nb_path)
            analyzer = StateAnalyzer()
            # No notebook_path → old behavior
            analysis = analyzer.analyze(adapter)

            never_executed = [
                i for i in analysis.issues if "never executed" in i.message
            ]
            # Cell 0 has no execution_count → reported as never executed
            assert len(never_executed) == 1
            assert never_executed[0].cell_index == 0


# ---------------------------------------------------------------------------
# JupyterAdapter: bounds checking and error handling
# ---------------------------------------------------------------------------

class TestJupyterAdapterEdgeCases:
    def test_get_cell_out_of_range(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            nb_path = _make_notebook(tmpdir, [("x = 1", None)])
            adapter = JupyterAdapter(nb_path)

            with pytest.raises(IndexError, match="out of range"):
                adapter.get_cell(999)

    def test_update_cell_out_of_range(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            nb_path = _make_notebook(tmpdir, [("x = 1", None)])
            adapter = JupyterAdapter(nb_path)

            with pytest.raises(IndexError, match="out of range"):
                adapter.update_cell(999, "y = 2")

    def test_load_nonexistent_file(self):
        with pytest.raises(FileNotFoundError, match="not found"):
            JupyterAdapter("/nonexistent/path.ipynb")

    def test_empty_notebook(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            nb_path = _make_notebook(tmpdir, [])
            adapter = JupyterAdapter(nb_path)
            assert adapter.cells == []
            assert adapter.code_cells == []

"""Tests for context command and state tracker."""

import tempfile
from pathlib import Path

from dasa.session.context import ContextManager
from dasa.session.log import SessionLog
from dasa.session.state import StateTracker


class TestStateTracker:
    def test_update_and_check(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = StateTracker(tmpdir)
            tracker.update_cell("test.ipynb", 0, "x = 1")
            assert not tracker.is_stale("test.ipynb", 0, "x = 1")

    def test_stale_after_change(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = StateTracker(tmpdir)
            tracker.update_cell("test.ipynb", 0, "x = 1")
            assert tracker.is_stale("test.ipynb", 0, "x = 2")

    def test_never_run_is_stale(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = StateTracker(tmpdir)
            assert tracker.is_stale("test.ipynb", 0, "x = 1")

    def test_get_stale_cells(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = StateTracker(tmpdir)
            tracker.update_cell("test.ipynb", 0, "x = 1")
            tracker.update_cell("test.ipynb", 1, "y = 2")

            cells = [(0, "x = 1"), (1, "y = CHANGED"), (2, "z = 3")]
            stale = tracker.get_stale_cells("test.ipynb", cells)
            assert 0 not in stale  # unchanged
            assert 1 in stale     # changed
            assert 2 in stale     # never run


class TestErrorContext:
    def test_fuzzy_match(self):
        from dasa.analysis.error_context import _fuzzy_match
        assert _fuzzy_match("revenue_usd", ["revenue", "cost", "region"]) == "revenue"

    def test_extract_name_from_error(self):
        from dasa.analysis.error_context import _extract_name_from_error
        name = _extract_name_from_error("name 'train_model' is not defined")
        assert name == "train_model"

    def test_no_match(self):
        from dasa.analysis.error_context import _fuzzy_match
        assert _fuzzy_match("xyz123", ["a", "b", "c"]) is None


class TestContextWorkflow:
    def test_full_context_workflow(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ctx_mgr = ContextManager(tmpdir)
            log = SessionLog(tmpdir)

            # Set goal
            ctx_mgr.ensure_session()
            ctx_mgr.update(goal="Predict churn", name="churn_project")
            log.append("user", "Goal: Predict churn")

            # Read back
            ctx = ctx_mgr.read()
            assert ctx.goal == "Predict churn"
            assert ctx.name == "churn_project"

            # Update status
            ctx_mgr.update(status="feature engineering")
            ctx = ctx_mgr.read()
            assert ctx.status == "feature engineering"

            # Check log
            entries = log.read()
            assert len(entries) == 1
            assert "Predict churn" in entries[0]

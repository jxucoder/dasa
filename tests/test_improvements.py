"""Tests for high-ROI improvements: loader, CSV profiler, scoped sessions, cached columns."""

import csv
import os
import tempfile

import pytest

from dasa.notebook.loader import get_adapter
from dasa.notebook.jupyter import JupyterAdapter
from dasa.notebook.marimo import MarimoAdapter
from dasa.analysis.profiler import profile_csv, Profiler, ColumnProfile, DataFrameProfile
from dasa.analysis.error_context import _get_cached_columns, _fuzzy_match
from dasa.session.scope import notebook_session_dir
from dasa.session.log import SessionLog
from dasa.session.profiles import ProfileCache
from dasa.session.state import StateTracker


# ── get_adapter ──────────────────────────────────────────────────────

class TestGetAdapter:
    def test_ipynb_returns_jupyter(self, tmp_path):
        # Create a minimal .ipynb
        nb_path = tmp_path / "test.ipynb"
        nb_path.write_text('{"nbformat": 4, "nbformat_minor": 5, "metadata": {}, "cells": []}')
        adapter = get_adapter(str(nb_path))
        assert isinstance(adapter, JupyterAdapter)

    def test_py_returns_marimo(self, tmp_path):
        py_path = tmp_path / "test.py"
        py_path.write_text("import marimo as mo\napp = mo.App()\n")
        adapter = get_adapter(str(py_path))
        assert isinstance(adapter, MarimoAdapter)

    def test_unsupported_format_raises(self, tmp_path):
        txt_path = tmp_path / "test.txt"
        txt_path.write_text("hello")
        with pytest.raises(ValueError, match="Unsupported notebook format"):
            get_adapter(str(txt_path))


# ── CSV profiling ────────────────────────────────────────────────────

class TestProfileCSV:
    def test_basic_csv(self, tmp_path):
        csv_path = tmp_path / "data.csv"
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["name", "age", "score"])
            writer.writerow(["Alice", "30", "95.5"])
            writer.writerow(["Bob", "25", "87.0"])
            writer.writerow(["Charlie", "35", "92.3"])

        profile = profile_csv(str(csv_path))
        assert profile.name == "data"
        assert profile.shape == (3, 3)
        assert len(profile.columns) == 3

        # name column should be object
        name_col = profile.columns[0]
        assert name_col.name == "name"
        assert name_col.dtype == "object"
        assert name_col.non_null_count == 3

        # age column should be numeric
        age_col = profile.columns[1]
        assert age_col.name == "age"
        assert age_col.dtype == "int64"
        assert age_col.min_val == 25.0
        assert age_col.max_val == 35.0

    def test_csv_with_nulls(self, tmp_path):
        csv_path = tmp_path / "nulls.csv"
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["x", "y"])
            writer.writerow(["1", ""])
            writer.writerow(["2", "10"])
            writer.writerow(["", "20"])

        profile = profile_csv(str(csv_path))
        assert profile.shape == (3, 2)

        x_col = profile.columns[0]
        assert x_col.null_count == 1
        assert x_col.null_percent > 0

    def test_csv_not_found(self):
        with pytest.raises(FileNotFoundError):
            profile_csv("/nonexistent/path.csv")

    def test_csv_empty(self, tmp_path):
        csv_path = tmp_path / "empty.csv"
        csv_path.write_text("")
        with pytest.raises(ValueError, match="Empty CSV"):
            profile_csv(str(csv_path))

    def test_csv_negative_values(self, tmp_path):
        csv_path = tmp_path / "neg.csv"
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["val"])
            writer.writerow(["-5"])
            writer.writerow(["10"])

        profile = profile_csv(str(csv_path))
        val_col = profile.columns[0]
        assert val_col.min_val == -5.0
        assert "has negative values" in val_col.issues


# ── Cached columns in error context ─────────────────────────────────

class TestCachedColumns:
    def test_cached_columns_from_dict(self, tmp_path):
        os.chdir(tmp_path)
        cache = ProfileCache()
        cache.save("df", {
            "name": "df",
            "shape": [100, 3],
            "columns": {
                "revenue": {"dtype": "float64"},
                "name": {"dtype": "object"},
                "date": {"dtype": "datetime64"},
            },
        })

        # Source referencing df[...]
        cols = _get_cached_columns("df['revenu']")
        assert cols is not None
        assert "revenue" in cols
        assert "name" in cols

    def test_cached_columns_miss(self, tmp_path):
        os.chdir(tmp_path)
        cols = _get_cached_columns("unknown_var['col']")
        assert cols is None

    def test_fuzzy_match(self):
        assert _fuzzy_match("revenu", ["revenue", "name", "date"]) == "revenue"
        assert _fuzzy_match("xyz123", ["a", "b", "c"]) is None


# ── Notebook-scoped sessions ─────────────────────────────────────────

class TestNotebookScopedSessions:
    def test_session_dir_created(self, tmp_path):
        session_dir = notebook_session_dir("analysis.ipynb", project_dir=str(tmp_path))
        assert "analysis" in session_dir
        assert os.path.isdir(session_dir)

    def test_scoped_log(self, tmp_path):
        session_dir = notebook_session_dir("nb1.ipynb", project_dir=str(tmp_path))
        log = SessionLog(session_dir=session_dir)
        log.append("test", "hello from nb1")
        entries = log.read()
        assert len(entries) == 1
        assert "hello from nb1" in entries[0]

        # Different notebook has separate log
        session_dir2 = notebook_session_dir("nb2.ipynb", project_dir=str(tmp_path))
        log2 = SessionLog(session_dir=session_dir2)
        assert log2.read() == []

    def test_scoped_profile_cache(self, tmp_path):
        session_dir = notebook_session_dir("test.ipynb", project_dir=str(tmp_path))
        cache = ProfileCache(session_dir=session_dir)
        cache.save("df", {"shape": [10, 2]})
        loaded = cache.load("df")
        assert loaded["shape"] == [10, 2]

        # Global cache shouldn't have it
        global_cache = ProfileCache(project_dir=str(tmp_path))
        assert global_cache.load("df") is None

    def test_scoped_state_tracker(self, tmp_path):
        session_dir = notebook_session_dir("test.ipynb", project_dir=str(tmp_path))
        tracker = StateTracker(session_dir=session_dir)
        tracker.update_cell("test.ipynb", 0, "x = 1")
        assert not tracker.is_stale("test.ipynb", 0, "x = 1")
        assert tracker.is_stale("test.ipynb", 0, "x = 2")


# ── DataFrameProfile.to_dict round-trip ──────────────────────────────

class TestProfileRoundtrip:
    def test_csv_profile_to_dict(self, tmp_path):
        csv_path = tmp_path / "rt.csv"
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["a", "b"])
            writer.writerow(["1", "hello"])
            writer.writerow(["2", "world"])

        profile = profile_csv(str(csv_path))
        d = profile.to_dict()
        assert d["name"] == "rt"
        assert d["shape"] == [2, 2]
        assert "a" in d["columns"]
        assert "b" in d["columns"]

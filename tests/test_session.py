"""Tests for session management."""

import tempfile
from pathlib import Path

from dasa.session.context import ContextManager, ProjectContext
from dasa.session.log import SessionLog
from dasa.session.profiles import ProfileCache


class TestContextManager:
    def test_ensure_session_creates_dirs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = ContextManager(tmpdir)
            mgr.ensure_session()
            assert (Path(tmpdir) / ".dasa").is_dir()
            assert (Path(tmpdir) / ".dasa" / "profiles").is_dir()
            assert (Path(tmpdir) / ".dasa" / "log").exists()

    def test_read_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = ContextManager(tmpdir)
            ctx = mgr.read()
            assert ctx.name is None
            assert ctx.goal is None

    def test_write_and_read(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = ContextManager(tmpdir)
            ctx = ProjectContext(name="test", goal="test goal")
            mgr.write(ctx)
            read_ctx = mgr.read()
            assert read_ctx.name == "test"
            assert read_ctx.goal == "test goal"

    def test_update(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = ContextManager(tmpdir)
            mgr.update(name="test", goal="initial goal")
            mgr.update(goal="updated goal")
            ctx = mgr.read()
            assert ctx.name == "test"
            assert ctx.goal == "updated goal"


class TestSessionLog:
    def test_append_and_read(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log = SessionLog(tmpdir)
            # Ensure .dasa dir exists
            (Path(tmpdir) / ".dasa").mkdir()
            log.append("test", "hello world")
            entries = log.read()
            assert len(entries) == 1
            assert "hello world" in entries[0]
            assert "[test]" in entries[0]

    def test_read_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log = SessionLog(tmpdir)
            entries = log.read()
            assert entries == []

    def test_read_last_n(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log = SessionLog(tmpdir)
            (Path(tmpdir) / ".dasa").mkdir()
            for i in range(10):
                log.append("test", f"message {i}")
            entries = log.read(last_n=3)
            assert len(entries) == 3
            assert "message 9" in entries[-1]


class TestProfileCache:
    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ProfileCache(tmpdir)
            profile = {"name": "df", "shape": [100, 5], "columns": {"a": {"dtype": "int64"}}}
            cache.save("df", profile)
            loaded = cache.load("df")
            assert loaded["name"] == "df"
            assert loaded["shape"] == [100, 5]

    def test_load_nonexistent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ProfileCache(tmpdir)
            assert cache.load("nonexistent") is None

    def test_list_profiles(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ProfileCache(tmpdir)
            cache.save("df", {"name": "df"})
            cache.save("model", {"name": "model"})
            profiles = cache.list_profiles()
            assert "df" in profiles
            assert "model" in profiles

"""Notebook-scoped session directories."""

from pathlib import Path


def notebook_session_dir(notebook_path: str, project_dir: str = ".") -> str:
    """Return the session directory scoped to a specific notebook.

    Layout: .dasa/notebooks/<notebook_stem>/
    This keeps profiles, state, and logs separate per notebook.
    """
    stem = Path(notebook_path).stem
    scoped = Path(project_dir) / ".dasa" / "notebooks" / stem
    scoped.mkdir(parents=True, exist_ok=True)
    return str(scoped)

"""Notebook loader — auto-detect format and return appropriate adapter."""

from pathlib import Path

from .base import NotebookAdapter


def get_adapter(path: str) -> NotebookAdapter:
    """Return the right adapter based on file extension.

    - .ipynb -> JupyterAdapter
    - .py   -> MarimoAdapter
    """
    ext = Path(path).suffix.lower()

    if ext == ".ipynb":
        from .jupyter import JupyterAdapter
        return JupyterAdapter(path)
    elif ext == ".py":
        from .marimo import MarimoAdapter
        return MarimoAdapter(path)
    else:
        raise ValueError(
            f"Unsupported notebook format '{ext}'. "
            "Supported: .ipynb (Jupyter), .py (Marimo)"
        )

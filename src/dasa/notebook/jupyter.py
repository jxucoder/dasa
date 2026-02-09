"""Jupyter .ipynb adapter using nbformat."""

from pathlib import Path
from typing import Optional

import nbformat

from .base import Cell, NotebookAdapter


class JupyterAdapter(NotebookAdapter):
    """Adapter for Jupyter .ipynb notebooks."""

    def __init__(self, path: str | None = None):
        self._nb: Optional[nbformat.NotebookNode] = None
        self._path: Optional[Path] = None
        if path:
            self.load(path)

    def load(self, path: str) -> None:
        """Load notebook from path."""
        self._path = Path(path)
        if not self._path.exists():
            raise FileNotFoundError(f"Notebook not found: {path}")
        try:
            with open(self._path) as f:
                self._nb = nbformat.read(f, as_version=4)
        except Exception as e:
            raise ValueError(f"Failed to read notebook {path}: {e}") from e

    def save(self, path: str | None = None) -> None:
        """Save notebook to path."""
        save_path = Path(path) if path else self._path
        if save_path is None:
            raise ValueError("No path specified and no path loaded")
        with open(save_path, "w") as f:
            nbformat.write(self._nb, f)

    @property
    def cells(self) -> list[Cell]:
        """Return all cells."""
        if self._nb is None:
            return []
        result = []
        for i, cell in enumerate(self._nb.cells):
            result.append(Cell(
                index=i,
                cell_type=cell.cell_type,
                source=cell.source,
                outputs=cell.get("outputs", []),
                execution_count=cell.get("execution_count"),
            ))
        return result

    def get_cell(self, index: int) -> Cell:
        """Get cell by index."""
        if self._nb is None:
            raise ValueError("No notebook loaded")
        if index < 0 or index >= len(self._nb.cells):
            raise IndexError(
                f"Cell index {index} out of range "
                f"(notebook has {len(self._nb.cells)} cells, indices 0-{len(self._nb.cells) - 1})"
            )
        cell = self._nb.cells[index]
        return Cell(
            index=index,
            cell_type=cell.cell_type,
            source=cell.source,
            outputs=cell.get("outputs", []),
            execution_count=cell.get("execution_count"),
        )

    def update_cell(self, index: int, source: str) -> None:
        """Update cell source code."""
        if self._nb is None:
            raise ValueError("No notebook loaded")
        if index < 0 or index >= len(self._nb.cells):
            raise IndexError(
                f"Cell index {index} out of range "
                f"(notebook has {len(self._nb.cells)} cells)"
            )
        self._nb.cells[index].source = source

    @property
    def raw_notebook(self) -> nbformat.NotebookNode:
        """Access the raw nbformat notebook object."""
        return self._nb

    @property
    def path(self) -> Optional[Path]:
        """Return the loaded path."""
        return self._path

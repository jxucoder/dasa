"""Jupyter notebook (.ipynb) adapter."""

from pathlib import Path
from typing import Any, Optional

import nbformat
from nbformat import NotebookNode

from .base import Cell, NotebookAdapter


class JupyterAdapter(NotebookAdapter):
    """Adapter for Jupyter .ipynb notebooks."""

    def __init__(self, path: Optional[str] = None):
        self.path: Optional[Path] = None
        self._notebook: Optional[NotebookNode] = None

        if path:
            self.load(path)

    def load(self, path: str) -> None:
        """Load notebook from .ipynb file."""
        self.path = Path(path)
        with open(self.path) as f:
            self._notebook = nbformat.read(f, as_version=4)

    def save(self, path: Optional[str] = None) -> None:
        """Save notebook to file."""
        save_path = Path(path) if path else self.path
        if not save_path:
            raise ValueError("No path specified")

        with open(save_path, 'w') as f:
            nbformat.write(self._notebook, f)

    @property
    def cells(self) -> list[Cell]:
        """Get all cells as Cell objects."""
        if not self._notebook:
            return []

        return [
            Cell(
                index=i,
                cell_type=c.cell_type,
                source=c.source,
                outputs=list(getattr(c, 'outputs', [])),
                execution_count=getattr(c, 'execution_count', None),
                metadata=dict(c.metadata)
            )
            for i, c in enumerate(self._notebook.cells)
        ]

    def get_cell(self, index: int) -> Cell:
        """Get cell by index."""
        cells = self.cells
        if index < 0 or index >= len(cells):
            raise IndexError(f"Cell index {index} out of range")
        return cells[index]

    def add_cell(
        self,
        source: str,
        cell_type: str = "code",
        index: Optional[int] = None
    ) -> Cell:
        """Add a new cell at the specified index."""
        if not self._notebook:
            raise ValueError("No notebook loaded")

        if cell_type == "code":
            new_cell = nbformat.v4.new_code_cell(source)
        elif cell_type == "markdown":
            new_cell = nbformat.v4.new_markdown_cell(source)
        else:
            new_cell = nbformat.v4.new_raw_cell(source)

        if index is None:
            index = len(self._notebook.cells)

        self._notebook.cells.insert(index, new_cell)

        return Cell(
            index=index,
            cell_type=cell_type,
            source=source,
            outputs=[],
            execution_count=None,
            metadata={}
        )

    def update_cell(self, index: int, source: str) -> None:
        """Update cell source code."""
        if not self._notebook:
            raise ValueError("No notebook loaded")

        if index < 0 or index >= len(self._notebook.cells):
            raise IndexError(f"Cell index {index} out of range")

        self._notebook.cells[index].source = source

    def delete_cell(self, index: int) -> None:
        """Delete cell at index."""
        if not self._notebook:
            raise ValueError("No notebook loaded")

        if index < 0 or index >= len(self._notebook.cells):
            raise IndexError(f"Cell index {index} out of range")

        del self._notebook.cells[index]

    def move_cell(self, from_index: int, to_index: int) -> None:
        """Move a cell from one position to another."""
        if not self._notebook:
            raise ValueError("No notebook loaded")

        if from_index < 0 or from_index >= len(self._notebook.cells):
            raise IndexError(f"Source cell index {from_index} out of range")

        if to_index < 0 or to_index > len(self._notebook.cells):
            raise IndexError(f"Target cell index {to_index} out of range")

        cell = self._notebook.cells.pop(from_index)
        self._notebook.cells.insert(to_index, cell)

    @property
    def execution_order(self) -> list[int]:
        """Get actual execution order from execution counts."""
        if not self._notebook:
            return []

        cells_with_count = [
            (i, c.execution_count)
            for i, c in enumerate(self._notebook.cells)
            if c.cell_type == "code" and c.execution_count is not None
        ]

        # Sort by execution count to get order
        sorted_cells = sorted(cells_with_count, key=lambda x: x[1])
        return [i for i, _ in sorted_cells]

    @property
    def kernel_spec(self) -> Optional[str]:
        """Get kernel specification name."""
        if not self._notebook:
            return None
        return self._notebook.metadata.get('kernelspec', {}).get('name')

    @property
    def raw_notebook(self) -> Optional[NotebookNode]:
        """Get the raw nbformat notebook object."""
        return self._notebook

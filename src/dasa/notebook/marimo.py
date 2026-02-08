"""Marimo notebook (.py) adapter."""

import ast
import re
from pathlib import Path
from typing import Optional

from .base import Cell, NotebookAdapter


class MarimoAdapter(NotebookAdapter):
    """Adapter for Marimo .py notebooks."""

    def __init__(self, path: str | None = None):
        self._cells: list[Cell] = []
        self._path: Optional[Path] = None
        self._source: str = ""
        if path:
            self.load(path)

    def load(self, path: str) -> None:
        """Parse .py file and extract @app.cell functions."""
        self._path = Path(path)
        self._source = self._path.read_text()

        try:
            tree = ast.parse(self._source)
        except SyntaxError:
            self._cells = []
            return

        self._cells = []
        cell_index = 0
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.FunctionDef) and self._is_cell_function(node):
                cell = self._parse_cell(node, cell_index)
                self._cells.append(cell)
                cell_index += 1

    def save(self, path: str | None = None) -> None:
        """Save is not directly supported for Marimo files."""
        raise NotImplementedError(
            "Marimo adapter is read-only. Edit the .py file directly."
        )

    @property
    def cells(self) -> list[Cell]:
        """Return all cells."""
        return self._cells

    def get_cell(self, index: int) -> Cell:
        """Get cell by index."""
        return self._cells[index]

    def update_cell(self, index: int, source: str) -> None:
        """Update not supported for Marimo files."""
        raise NotImplementedError(
            "Marimo adapter is read-only. Edit the .py file directly."
        )

    @property
    def path(self) -> Optional[Path]:
        return self._path

    @property
    def dependencies(self) -> dict[int, list[str]]:
        """Get explicit dependencies for each cell from function arguments."""
        deps = {}
        for cell in self._cells:
            # Dependencies are the function parameters
            deps[cell.index] = list(cell.outputs) if hasattr(cell, '_deps') else []
        return deps

    def _is_cell_function(self, node: ast.FunctionDef) -> bool:
        """Check if function has @app.cell decorator."""
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Attribute):
                if decorator.attr == "cell":
                    return True
            elif isinstance(decorator, ast.Call):
                func = decorator.func
                if isinstance(func, ast.Attribute) and func.attr == "cell":
                    return True
        return False

    def _parse_cell(self, node: ast.FunctionDef, index: int) -> Cell:
        """Extract cell info from function definition."""
        # Get function body source (skip the def line and decorator)
        body_lines = []
        source_lines = self._source.splitlines()
        # Find the body start (after def line and colon)
        body_start = node.body[0].lineno - 1 if node.body else node.lineno
        body_end = node.end_lineno if hasattr(node, 'end_lineno') and node.end_lineno else body_start + 1

        for i in range(body_start, min(body_end, len(source_lines))):
            body_lines.append(source_lines[i])

        # Dedent the body
        if body_lines:
            # Find minimum indentation
            non_empty = [line for line in body_lines if line.strip()]
            if non_empty:
                min_indent = min(len(line) - len(line.lstrip()) for line in non_empty)
                body_lines = [line[min_indent:] if len(line) > min_indent else line.strip()
                              for line in body_lines]

        source = "\n".join(body_lines)

        # Extract dependencies from function arguments
        deps = [arg.arg for arg in node.args.args]

        cell = Cell(
            index=index,
            cell_type="code",
            source=source,
            outputs=[],
            execution_count=index + 1,  # Marimo cells are always "executed"
        )
        cell._deps = deps  # Store dependencies as private attribute
        return cell

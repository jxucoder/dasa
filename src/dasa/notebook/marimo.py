"""Marimo notebook (.py) adapter."""

import ast
import re
from pathlib import Path
from typing import Optional

from .base import Cell, NotebookAdapter


class MarimoCell:
    """Represents a parsed Marimo cell."""

    def __init__(
        self,
        index: int,
        name: str,
        source: str,
        inputs: list[str],
        outputs: list[str]
    ):
        self.index = index
        self.name = name
        self.source = source
        self.inputs = inputs  # Function parameters (dependencies)
        self.outputs = outputs  # Return values


class MarimoAdapter(NotebookAdapter):
    """Adapter for Marimo notebooks (.py files with @app.cell decorators)."""

    def __init__(self, path: Optional[str] = None):
        self.path: Optional[Path] = None
        self._cells: list[MarimoCell] = []
        self._raw_content: str = ""
        self._app_var: str = "app"

        if path:
            self.load(path)

    def load(self, path: str) -> None:
        """Load Marimo notebook from .py file."""
        self.path = Path(path)
        self._raw_content = self.path.read_text()
        self._parse_cells()

    def _parse_cells(self) -> None:
        """Parse @app.cell decorated functions."""
        self._cells = []

        # Find the app variable name
        app_match = re.search(r'(\w+)\s*=\s*marimo\.App\(\)', self._raw_content)
        if app_match:
            self._app_var = app_match.group(1)

        # Parse AST
        try:
            tree = ast.parse(self._raw_content)
        except SyntaxError:
            return

        cell_index = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check for @app.cell decorator
                is_cell = False
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Attribute):
                        if (isinstance(decorator.value, ast.Name) and
                            decorator.value.id == self._app_var and
                            decorator.attr == "cell"):
                            is_cell = True
                            break
                    elif isinstance(decorator, ast.Call):
                        if isinstance(decorator.func, ast.Attribute):
                            if (isinstance(decorator.func.value, ast.Name) and
                                decorator.func.value.id == self._app_var and
                                decorator.func.attr == "cell"):
                                is_cell = True
                                break

                if is_cell:
                    # Extract function details
                    func_name = node.name
                    inputs = [arg.arg for arg in node.args.args]

                    # Extract return values
                    outputs = []
                    for stmt in ast.walk(node):
                        if isinstance(stmt, ast.Return) and stmt.value:
                            if isinstance(stmt.value, ast.Tuple):
                                for elt in stmt.value.elts:
                                    if isinstance(elt, ast.Name):
                                        outputs.append(elt.id)
                            elif isinstance(stmt.value, ast.Name):
                                outputs.append(stmt.value.id)

                    # Extract source (function body)
                    source_lines = self._raw_content.split('\n')
                    start_line = node.lineno - 1
                    end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line + 1

                    # Get just the function body (skip decorator and def line)
                    body_lines = []
                    in_body = False
                    for i in range(start_line, end_line):
                        line = source_lines[i]
                        if in_body:
                            # Remove one level of indentation
                            if line.startswith('    '):
                                body_lines.append(line[4:])
                            else:
                                body_lines.append(line)
                        elif line.strip().startswith('def '):
                            in_body = True

                    source = '\n'.join(body_lines).strip()
                    # Remove return statement for cleaner source
                    if source.endswith(','):
                        source = source[:-1]

                    self._cells.append(MarimoCell(
                        index=cell_index,
                        name=func_name,
                        source=source,
                        inputs=inputs,
                        outputs=outputs
                    ))
                    cell_index += 1

    def save(self, path: Optional[str] = None) -> None:
        """Save notebook to file."""
        save_path = Path(path) if path else self.path
        if not save_path:
            raise ValueError("No path specified")

        # For now, just save the raw content
        # A more sophisticated implementation would reconstruct the file
        save_path.write_text(self._raw_content)

    @property
    def cells(self) -> list[Cell]:
        """Get all cells as Cell objects."""
        return [
            Cell(
                index=c.index,
                cell_type="code",
                source=c.source,
                outputs=[],
                execution_count=None,
                metadata={"marimo_name": c.name, "inputs": c.inputs, "outputs": c.outputs}
            )
            for c in self._cells
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
        """Add a new cell."""
        # Marimo cells need to be functions - wrap the source
        func_name = f"cell_{len(self._cells)}"
        wrapped = f"\n@{self._app_var}.cell\ndef {func_name}():\n    " + source.replace('\n', '\n    ') + "\n    return\n"

        # Insert into raw content (simplified)
        self._raw_content += wrapped
        self._parse_cells()

        return self.get_cell(len(self._cells) - 1)

    def update_cell(self, index: int, source: str) -> None:
        """Update cell source."""
        # This would require sophisticated AST manipulation
        # Simplified implementation: update the MarimoCell
        if index < 0 or index >= len(self._cells):
            raise IndexError(f"Cell index {index} out of range")

        self._cells[index].source = source
        # Note: This doesn't update the raw content
        # A full implementation would need to regenerate the file

    def delete_cell(self, index: int) -> None:
        """Delete a cell."""
        if index < 0 or index >= len(self._cells):
            raise IndexError(f"Cell index {index} out of range")

        del self._cells[index]
        # Reindex remaining cells
        for i, cell in enumerate(self._cells):
            cell.index = i

    @property
    def execution_order(self) -> list[int]:
        """Get execution order based on dependencies."""
        # In Marimo, execution order is determined by dependency graph
        # Build a simple topological sort based on inputs/outputs
        order = []
        remaining = set(range(len(self._cells)))
        provided = set()

        while remaining:
            # Find cells whose inputs are all satisfied
            ready = []
            for idx in remaining:
                cell = self._cells[idx]
                if all(inp in provided for inp in cell.inputs):
                    ready.append(idx)

            if not ready:
                # Circular dependency or missing inputs - add remaining in order
                order.extend(sorted(remaining))
                break

            # Add ready cells and their outputs
            for idx in sorted(ready):
                order.append(idx)
                remaining.remove(idx)
                provided.update(self._cells[idx].outputs)

        return order

    @property
    def kernel_spec(self) -> Optional[str]:
        """Marimo uses Python."""
        return "python3"

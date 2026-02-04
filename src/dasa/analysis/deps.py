"""Cell dependency analysis."""

from dataclasses import dataclass, field

from dasa.notebook.base import NotebookAdapter
from dasa.analysis.parser import parse_cell


@dataclass
class CellNode:
    """A cell in the dependency graph."""
    index: int
    preview: str
    definitions: set[str]
    references: set[str]
    upstream: set[int] = field(default_factory=set)  # Cells this depends on
    downstream: set[int] = field(default_factory=set)  # Cells that depend on this


@dataclass
class DependencyGraph:
    """Complete dependency graph for a notebook."""
    nodes: dict[int, CellNode]

    def get_upstream(self, cell_index: int) -> list[int]:
        """Get all cells this cell depends on (transitively)."""
        if cell_index not in self.nodes:
            return []

        visited: set[int] = set()
        queue = list(self.nodes[cell_index].upstream)

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            queue.extend(self.nodes[current].upstream)

        return sorted(visited)

    def get_downstream(self, cell_index: int) -> list[int]:
        """Get all cells affected by changes to this cell (transitively)."""
        if cell_index not in self.nodes:
            return []

        visited: set[int] = set()
        queue = list(self.nodes[cell_index].downstream)

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            queue.extend(self.nodes[current].downstream)

        return sorted(visited)


class DependencyAnalyzer:
    """Analyzes cell dependencies in a notebook."""

    def build_graph(self, adapter: NotebookAdapter) -> DependencyGraph:
        """Build dependency graph from notebook."""

        nodes: dict[int, CellNode] = {}
        var_definitions: dict[str, int] = {}  # var -> cell that last defined it

        # First pass: parse all cells
        for cell in adapter.code_cells:
            analysis = parse_cell(cell.source)

            nodes[cell.index] = CellNode(
                index=cell.index,
                preview=cell.preview,
                definitions=analysis.definitions,
                references=analysis.references
            )

        # Second pass: build edges
        for cell in adapter.code_cells:
            node = nodes[cell.index]

            # Find upstream dependencies (cells that define vars we reference)
            for ref in node.references:
                if ref in var_definitions:
                    defining_cell = var_definitions[ref]
                    node.upstream.add(defining_cell)
                    nodes[defining_cell].downstream.add(cell.index)

            # Update definitions
            for defn in node.definitions:
                var_definitions[defn] = cell.index

        return DependencyGraph(nodes=nodes)

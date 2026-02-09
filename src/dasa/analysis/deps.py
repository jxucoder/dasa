"""Cell dependency graph analysis."""

from dataclasses import dataclass, field

from dasa.notebook.base import NotebookAdapter
from dasa.analysis.parser import parse_cell


@dataclass
class CellNode:
    """A node in the dependency graph."""
    index: int
    definitions: set[str] = field(default_factory=set)
    references: set[str] = field(default_factory=set)
    upstream: set[int] = field(default_factory=set)
    downstream: set[int] = field(default_factory=set)
    label: str = ""  # Short description from first line of code


@dataclass
class DependencyGraph:
    """Directed acyclic graph of cell dependencies."""
    nodes: dict[int, CellNode] = field(default_factory=dict)

    def get_upstream(self, cell_index: int) -> list[int]:
        """Get all cells this cell depends on (transitively)."""
        visited = set()
        self._walk_upstream(cell_index, visited)
        visited.discard(cell_index)
        return sorted(visited)

    def get_downstream(self, cell_index: int) -> list[int]:
        """Get all cells that depend on this cell (transitively)."""
        visited = set()
        self._walk_downstream(cell_index, visited)
        visited.discard(cell_index)
        return sorted(visited)

    def _walk_upstream(self, cell_index: int, visited: set[int]) -> None:
        if cell_index in visited:
            return
        visited.add(cell_index)
        node = self.nodes.get(cell_index)
        if node:
            for up in node.upstream:
                self._walk_upstream(up, visited)

    def _walk_downstream(self, cell_index: int, visited: set[int]) -> None:
        if cell_index in visited:
            return
        visited.add(cell_index)
        node = self.nodes.get(cell_index)
        if node:
            for down in node.downstream:
                self._walk_downstream(down, visited)

    def to_dict(self) -> dict:
        return {
            idx: {
                "label": node.label,
                "definitions": sorted(node.definitions),
                "references": sorted(node.references),
                "upstream": sorted(node.upstream),
                "downstream": sorted(node.downstream),
            }
            for idx, node in sorted(self.nodes.items())
        }


class DependencyAnalyzer:
    """Build and query cell dependency graph."""

    def build_graph(self, adapter: NotebookAdapter) -> DependencyGraph:
        """Build dependency graph from notebook cells."""
        graph = DependencyGraph()
        code_cells = adapter.code_cells

        # Parse all cells first
        for cell in code_cells:
            analysis = parse_cell(cell.source)
            # Get label from first meaningful line
            label = self._get_label(cell.source)
            graph.nodes[cell.index] = CellNode(
                index=cell.index,
                definitions=analysis.definitions,
                references=analysis.references,
                label=label,
            )

        # Build dependency edges
        # For each cell, find which earlier cells define variables it references
        var_to_cell: dict[str, int] = {}

        for cell in code_cells:
            node = graph.nodes[cell.index]

            # Check references against known definitions
            for ref in node.references:
                if ref in var_to_cell:
                    defining_cell = var_to_cell[ref]
                    if defining_cell != cell.index:
                        node.upstream.add(defining_cell)
                        graph.nodes[defining_cell].downstream.add(cell.index)

            # Record definitions (overwrites previous definitions)
            for defn in node.definitions:
                var_to_cell[defn] = cell.index

        return graph

    def _get_label(self, source: str) -> str:
        """Extract a short label from cell source."""
        for line in source.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                # Truncate to reasonable length
                if len(stripped) > 50:
                    return stripped[:47] + "..."
                return stripped
            elif stripped.startswith("# "):
                return stripped[2:].strip()
        return ""

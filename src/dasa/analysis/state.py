"""Notebook state analysis."""

from dataclasses import dataclass, field
from typing import Optional

from dasa.notebook.base import NotebookAdapter
from dasa.analysis.parser import parse_cell


@dataclass
class StateIssue:
    """A state consistency issue."""
    severity: str  # "error", "warning"
    cell_index: int
    message: str
    suggestion: Optional[str] = None


@dataclass
class StateAnalysis:
    """Complete state analysis result."""
    is_consistent: bool
    issues: list[StateIssue]
    execution_order: list[int]
    correct_order: list[int]
    defined_vars: dict[str, int]  # var -> cell that defines it
    undefined_refs: list[tuple[int, str]]  # (cell, var) pairs


class StateAnalyzer:
    """Analyzes notebook state for consistency issues."""

    def analyze(self, adapter: NotebookAdapter) -> StateAnalysis:
        """Analyze notebook state."""

        issues: list[StateIssue] = []
        defined_vars: dict[str, int] = {}
        undefined_refs: list[tuple[int, str]] = []

        # Track what's defined at each point
        current_definitions: set[str] = set()

        for cell in adapter.code_cells:
            analysis = parse_cell(cell.source)

            # Check for undefined references
            for ref in analysis.references:
                if ref not in current_definitions:
                    undefined_refs.append((cell.index, ref))
                    issues.append(StateIssue(
                        severity="error",
                        cell_index=cell.index,
                        message=f"Uses undefined variable '{ref}'",
                        suggestion=f"Make sure a cell defining '{ref}' runs before this cell"
                    ))

            # Track definitions
            for defn in analysis.definitions:
                if defn in defined_vars and defined_vars[defn] != cell.index:
                    # Redefinition - might be intentional
                    pass
                defined_vars[defn] = cell.index
                current_definitions.add(defn)

        # Check execution order
        execution_order = adapter.execution_order
        correct_order = [c.index for c in adapter.code_cells]

        # Detect out-of-order execution
        if execution_order:
            # Check if execution order matches cell order
            cell_indices = [c.index for c in adapter.code_cells]
            exec_positions = {idx: pos for pos, idx in enumerate(execution_order)}

            for i, cell_idx in enumerate(cell_indices[:-1]):
                next_idx = cell_indices[i + 1]
                if cell_idx in exec_positions and next_idx in exec_positions:
                    if exec_positions[cell_idx] > exec_positions[next_idx]:
                        issues.append(StateIssue(
                            severity="warning",
                            cell_index=next_idx,
                            message=f"Executed before Cell {cell_idx} (out of order)",
                            suggestion="Re-run cells in order"
                        ))

        # Check for cells with no execution count (never run)
        for cell in adapter.code_cells:
            if cell.execution_count is None:
                issues.append(StateIssue(
                    severity="warning",
                    cell_index=cell.index,
                    message="Cell has never been executed",
                    suggestion="Run this cell"
                ))

        # Determine if consistent
        has_errors = any(i.severity == "error" for i in issues)

        return StateAnalysis(
            is_consistent=not has_errors,
            issues=issues,
            execution_order=execution_order,
            correct_order=correct_order,
            defined_vars=defined_vars,
            undefined_refs=undefined_refs
        )

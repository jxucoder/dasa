"""State consistency analysis for notebooks."""

from dataclasses import dataclass, field

from dasa.notebook.base import NotebookAdapter
from dasa.analysis.parser import parse_cell


@dataclass
class StateIssue:
    """A state consistency issue."""
    cell_index: int
    severity: str  # "error" or "warning"
    message: str


@dataclass
class StateAnalysis:
    """Result of state analysis."""
    is_consistent: bool
    issues: list[StateIssue] = field(default_factory=list)
    execution_order: list[int] = field(default_factory=list)
    correct_order: list[int] = field(default_factory=list)
    defined_vars: dict[str, int] = field(default_factory=dict)  # var -> defining cell
    undefined_refs: list[tuple[int, str]] = field(default_factory=list)  # (cell, var)

    def to_dict(self) -> dict:
        return {
            "is_consistent": self.is_consistent,
            "issues": [
                {"cell": i.cell_index, "severity": i.severity, "message": i.message}
                for i in self.issues
            ],
            "execution_order": self.execution_order,
            "correct_order": self.correct_order,
            "undefined_refs": [{"cell": c, "var": v} for c, v in self.undefined_refs],
        }


class StateAnalyzer:
    """Detect state inconsistencies in notebooks."""

    def analyze(self, adapter: NotebookAdapter) -> StateAnalysis:
        """Analyze notebook state consistency."""
        issues = []
        defined_vars: dict[str, int] = {}
        undefined_refs: list[tuple[int, str]] = []

        code_cells = adapter.code_cells

        # Track which variables are defined at each point
        for cell in code_cells:
            analysis = parse_cell(cell.source)

            # Check for undefined references
            for ref in analysis.references:
                if ref not in defined_vars:
                    undefined_refs.append((cell.index, ref))
                    issues.append(StateIssue(
                        cell_index=cell.index,
                        severity="error",
                        message=f"uses undefined variable '{ref}'",
                    ))

            # Record definitions
            for defn in analysis.definitions:
                defined_vars[defn] = cell.index

        # Check for never-executed cells
        for cell in code_cells:
            if cell.execution_count is None:
                issues.append(StateIssue(
                    cell_index=cell.index,
                    severity="warning",
                    message="never executed",
                ))

        # Check execution order
        execution_order = adapter.execution_order
        correct_order = [c.index for c in code_cells if c.execution_count is not None]

        if execution_order != correct_order:
            issues.append(StateIssue(
                cell_index=-1,
                severity="warning",
                message=f"out-of-order execution detected",
            ))

        is_consistent = not any(i.severity == "error" for i in issues)

        return StateAnalysis(
            is_consistent=is_consistent,
            issues=issues,
            execution_order=execution_order,
            correct_order=correct_order,
            defined_vars=defined_vars,
            undefined_refs=undefined_refs,
        )

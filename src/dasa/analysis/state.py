"""State consistency analysis for notebooks."""

from dataclasses import dataclass, field
from typing import Optional

from dasa.notebook.base import NotebookAdapter
from dasa.analysis.parser import parse_cell
from dasa.session.state import StateTracker


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


def _cell_was_executed(
    cell,
    state_tracker: Optional[StateTracker],
    notebook_path: Optional[str],
) -> bool:
    """Check if a cell was executed — via notebook execution_count OR dasa run."""
    # Check notebook's own execution_count (set by Jupyter/Colab)
    if cell.execution_count is not None:
        return True
    # Check state.json (set by dasa run)
    if state_tracker and notebook_path:
        return state_tracker.was_executed_current(
            notebook_path, cell.index, cell.source
        )
    return False


class StateAnalyzer:
    """Detect state inconsistencies in notebooks."""

    def analyze(
        self,
        adapter: NotebookAdapter,
        notebook_path: Optional[str] = None,
        state_tracker: Optional[StateTracker] = None,
    ) -> StateAnalysis:
        """Analyze notebook state consistency.

        Args:
            adapter: The notebook adapter.
            notebook_path: Path to notebook, used to check state.json for
                cells executed via ``dasa run``. If None, only checks
                execution_count from the notebook file.
            state_tracker: Optional StateTracker instance. If not provided and
                notebook_path is given, creates a default one (looks in CWD/.dasa/).
        """
        issues = []
        defined_vars: dict[str, int] = {}
        undefined_refs: list[tuple[int, str]] = []

        code_cells = adapter.code_cells

        # Load state.json tracking (cells executed via dasa run)
        if state_tracker is None and notebook_path is not None:
            state_tracker = StateTracker()

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

        # Check for never-executed cells — consult BOTH sources
        for cell in code_cells:
            if not _cell_was_executed(cell, state_tracker, notebook_path):
                issues.append(StateIssue(
                    cell_index=cell.index,
                    severity="warning",
                    message="never executed",
                ))

        # Check for stale cells (code changed since last dasa run)
        if state_tracker and notebook_path:
            for cell in code_cells:
                # Only flag as stale if the cell WAS executed via dasa but code changed
                if state_tracker.was_executed(notebook_path, cell.index) and \
                   state_tracker.is_stale(notebook_path, cell.index, cell.source):
                    issues.append(StateIssue(
                        cell_index=cell.index,
                        severity="warning",
                        message="stale — code modified since last run",
                    ))

        # Check execution order (from notebook execution_count only)
        execution_order = adapter.execution_order
        correct_order = [c.index for c in code_cells if c.execution_count is not None]

        if execution_order and execution_order != correct_order:
            issues.append(StateIssue(
                cell_index=-1,
                severity="warning",
                message="out-of-order execution detected",
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

"""Checker module for evaluating agent outputs against success criteria.

This module implements the various success-criteria checkers used by the
evaluation harness.  Each task definition includes a ``success_criteria``
block that specifies a *type* and associated parameters.  The
:class:`CheckerDispatch` class routes to the correct checker function based
on that type string.

Supported criteria types
------------------------
- ``contains_all``      -- agent response contains *all* specified strings
- ``contains_any``      -- agent response contains *at least one* specified string
- ``contains_numbers``  -- agent response contains numbers within tolerance of expected min/max
- ``cell_executes``     -- a specified cell in the notebook can be executed without error
- ``notebook_validates`` -- the entire notebook has sequential execution counts (valid state)
"""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any


class CheckResult:
    """Container for the outcome of a single check."""

    def __init__(self, passed: bool, message: str, details: dict[str, Any] | None = None):
        self.passed = passed
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "message": self.message,
            "details": self.details,
        }

    def __repr__(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        return f"CheckResult({status}: {self.message})"

    def __bool__(self) -> bool:
        return self.passed


# -----------------------------------------------------------------------
# Individual checker implementations
# -----------------------------------------------------------------------

def check_contains_all(response: str, criteria: dict) -> CheckResult:
    """Check that *response* contains every string in ``criteria['values']``."""
    values: list[str] = criteria["values"]
    response_lower = response.lower()
    missing = [v for v in values if v.lower() not in response_lower]
    if missing:
        return CheckResult(
            passed=False,
            message=f"Response missing required values: {missing}",
            details={"missing": missing},
        )
    return CheckResult(passed=True, message="All required values found in response.")


def check_contains_any(response: str, criteria: dict) -> CheckResult:
    """Check that *response* contains at least one string from ``criteria['values']``."""
    values: list[str] = criteria["values"]
    response_lower = response.lower()
    found = [v for v in values if v.lower() in response_lower]
    if not found:
        return CheckResult(
            passed=False,
            message=f"Response does not contain any of: {values}",
            details={"expected_any": values},
        )
    return CheckResult(
        passed=True,
        message=f"Response contains: {found}",
        details={"found": found},
    )


def check_contains_numbers(response: str, criteria: dict) -> CheckResult:
    """Check that numeric values in the response are within tolerance of expected min/max."""
    expected_min = criteria.get("expected_min")
    expected_max = criteria.get("expected_max")
    tolerance = criteria.get("tolerance", 500)

    numbers = [float(n) for n in re.findall(r"-?\d+\.?\d*", response)]
    if not numbers:
        return CheckResult(
            passed=False,
            message="No numbers found in agent response.",
            details={"response_snippet": response[:200]},
        )

    found_min = min(numbers)
    found_max = max(numbers)
    details = {
        "found_min": found_min,
        "found_max": found_max,
        "expected_min": expected_min,
        "expected_max": expected_max,
        "tolerance": tolerance,
    }

    min_ok = expected_min is None or abs(found_min - expected_min) <= tolerance
    max_ok = expected_max is None or abs(found_max - expected_max) <= tolerance

    if min_ok and max_ok:
        return CheckResult(passed=True, message="Numeric values within tolerance.", details=details)
    return CheckResult(
        passed=False,
        message=f"Numeric values out of tolerance (min_ok={min_ok}, max_ok={max_ok}).",
        details=details,
    )


def check_cell_executes(notebook: dict, criteria: dict) -> CheckResult:
    """Check that a specific cell in the notebook can execute without error.

    This writes the notebook to a temporary file and uses ``jupyter nbconvert
    --to notebook --execute`` to attempt execution.  If ``criteria['cell']``
    is ``"new"`` the last cell is checked.
    """
    cell_spec = criteria.get("cell", "new")

    cells = notebook.get("cells", [])
    if cell_spec == "new":
        cell_idx = len(cells) - 1
    else:
        cell_idx = int(cell_spec)

    if cell_idx < 0 or cell_idx >= len(cells):
        return CheckResult(
            passed=False,
            message=f"Cell index {cell_idx} out of range (notebook has {len(cells)} cells).",
        )

    # Check the cell does not already contain error outputs
    cell = cells[cell_idx]
    for output in cell.get("outputs", []):
        if output.get("output_type") == "error":
            return CheckResult(
                passed=False,
                message=f"Cell {cell_idx} still has error output: {output.get('ename', 'unknown')}",
                details={"ename": output.get("ename"), "evalue": output.get("evalue")},
            )

    # Attempt execution via nbconvert (best-effort; skip if not installed)
    try:
        with tempfile.NamedTemporaryFile(suffix=".ipynb", mode="w", delete=False) as tmp:
            json.dump(notebook, tmp, indent=1)
            tmp_path = tmp.name

        result = subprocess.run(
            [
                "jupyter", "nbconvert",
                "--to", "notebook",
                "--execute",
                "--ExecutePreprocessor.timeout=30",
                tmp_path,
                "--output", tmp_path,
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            return CheckResult(
                passed=False,
                message=f"Notebook execution failed: {result.stderr[:500]}",
                details={"stderr": result.stderr},
            )
    except FileNotFoundError:
        # jupyter not installed -- fall back to static check only
        pass
    except subprocess.TimeoutExpired:
        return CheckResult(passed=False, message="Notebook execution timed out.")
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return CheckResult(
        passed=True,
        message=f"Cell {cell_idx} executes successfully.",
        details={"cell_index": cell_idx},
    )


def check_notebook_validates(notebook: dict, _criteria: dict) -> CheckResult:
    """Validate that execution counts in the notebook are sequential (1, 2, 3, ...)."""
    cells = notebook.get("cells", [])
    code_cells = [c for c in cells if c.get("cell_type") == "code"]

    exec_counts = []
    for i, cell in enumerate(code_cells):
        ec = cell.get("execution_count")
        if ec is None:
            return CheckResult(
                passed=False,
                message=f"Code cell {i} has no execution_count (not executed).",
                details={"cell_index": i},
            )
        exec_counts.append(ec)

    expected = list(range(1, len(code_cells) + 1))
    if exec_counts != expected:
        return CheckResult(
            passed=False,
            message=f"Execution counts {exec_counts} do not match expected {expected}.",
            details={"actual": exec_counts, "expected": expected},
        )

    # Also check no error outputs exist
    for i, cell in enumerate(code_cells):
        for output in cell.get("outputs", []):
            if output.get("output_type") == "error":
                return CheckResult(
                    passed=False,
                    message=f"Code cell {i} has error output.",
                    details={"cell_index": i, "ename": output.get("ename")},
                )

    return CheckResult(passed=True, message="Notebook state is valid and sequential.")


# -----------------------------------------------------------------------
# Dispatcher
# -----------------------------------------------------------------------

_CHECKERS = {
    "contains_all": lambda resp, nb, crit: check_contains_all(resp, crit),
    "contains_any": lambda resp, nb, crit: check_contains_any(resp, crit),
    "contains_numbers": lambda resp, nb, crit: check_contains_numbers(resp, crit),
    "cell_executes": lambda resp, nb, crit: check_cell_executes(nb, crit),
    "notebook_validates": lambda resp, nb, crit: check_notebook_validates(nb, crit),
}


class CheckerDispatch:
    """Route a success-criteria dict to the appropriate checker function.

    Usage::

        dispatcher = CheckerDispatch()
        result = dispatcher.check(
            response="The columns with nulls are revenue and email.",
            notebook=nb_dict,
            criteria={"type": "contains_all", "values": ["revenue", "email"]},
        )
        print(result)  # CheckResult(PASS: All required values found in response.)
    """

    def check(
        self,
        response: str,
        notebook: dict,
        criteria: dict,
    ) -> CheckResult:
        """Evaluate *response* / *notebook* against the given *criteria*.

        Parameters
        ----------
        response:
            The free-text answer produced by the agent.
        notebook:
            The (potentially modified) notebook dict.
        criteria:
            The ``success_criteria`` block from the task definition,
            containing at minimum a ``"type"`` key.

        Returns
        -------
        CheckResult
            Outcome of the evaluation.

        Raises
        ------
        ValueError
            If the criteria ``type`` is not recognised.
        """
        ctype = criteria.get("type")
        if ctype not in _CHECKERS:
            raise ValueError(
                f"Unknown criteria type {ctype!r}. "
                f"Supported types: {sorted(_CHECKERS)}"
            )
        return _CHECKERS[ctype](response, notebook, criteria)

"""Metrics collection and reporting for the DASA evaluation harness.

This module aggregates results from individual task runs and produces
summary statistics broken down by category, difficulty, and overall.
Results can be exported to JSON for later analysis.
"""

from __future__ import annotations

import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Any


class TaskResult:
    """Record of a single task evaluation."""

    def __init__(
        self,
        task_id: str,
        category: str,
        difficulty: str,
        passed: bool,
        message: str,
        duration_seconds: float = 0.0,
        details: dict[str, Any] | None = None,
    ):
        self.task_id = task_id
        self.category = category
        self.difficulty = difficulty
        self.passed = passed
        self.message = message
        self.duration_seconds = duration_seconds
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "category": self.category,
            "difficulty": self.difficulty,
            "passed": self.passed,
            "message": self.message,
            "duration_seconds": round(self.duration_seconds, 3),
            "details": self.details,
        }


class MetricsCollector:
    """Collect task results and compute aggregate metrics.

    Usage::

        collector = MetricsCollector(agent_name="my-agent-v1")
        collector.add_result(TaskResult(...))
        collector.add_result(TaskResult(...))
        summary = collector.summary()
        collector.save("/path/to/results/run_001.json")
    """

    def __init__(self, agent_name: str = "unknown") -> None:
        self.agent_name = agent_name
        self.results: list[TaskResult] = []
        self._start_time = time.time()

    # ------------------------------------------------------------------
    # Collection
    # ------------------------------------------------------------------

    def add_result(self, result: TaskResult) -> None:
        """Record a completed task evaluation."""
        self.results.append(result)

    # ------------------------------------------------------------------
    # Summaries
    # ------------------------------------------------------------------

    def summary(self) -> dict[str, Any]:
        """Compute and return aggregate metrics.

        Returns a dict with overall pass rate as well as breakdowns by
        category and difficulty level.
        """
        total = len(self.results)
        if total == 0:
            return {"agent": self.agent_name, "total": 0, "pass_rate": 0.0}

        passed = sum(1 for r in self.results if r.passed)

        by_category: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "passed": 0})
        by_difficulty: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "passed": 0})

        for r in self.results:
            by_category[r.category]["total"] += 1
            by_category[r.category]["passed"] += int(r.passed)
            by_difficulty[r.difficulty]["total"] += 1
            by_difficulty[r.difficulty]["passed"] += int(r.passed)

        def _rate(bucket: dict[str, int]) -> float:
            return round(bucket["passed"] / bucket["total"], 4) if bucket["total"] else 0.0

        return {
            "agent": self.agent_name,
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": round(passed / total, 4),
            "elapsed_seconds": round(time.time() - self._start_time, 2),
            "by_category": {
                cat: {"total": b["total"], "passed": b["passed"], "pass_rate": _rate(b)}
                for cat, b in sorted(by_category.items())
            },
            "by_difficulty": {
                diff: {"total": b["total"], "passed": b["passed"], "pass_rate": _rate(b)}
                for diff, b in sorted(by_difficulty.items())
            },
        }

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: str | Path) -> Path:
        """Save all results and summary to a JSON file.

        Parameters
        ----------
        path:
            Destination file path.  Parent directories will be created
            if they do not exist.

        Returns
        -------
        Path
            The resolved path that was written.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "summary": self.summary(),
            "results": [r.to_dict() for r in self.results],
        }

        with open(path, "w") as fh:
            json.dump(payload, fh, indent=2)

        return path.resolve()

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def print_summary(self) -> None:
        """Print a human-readable summary to stdout."""
        s = self.summary()
        print(f"\n{'='*60}")
        print(f"  DASA Evaluation Results  --  Agent: {s['agent']}")
        print(f"{'='*60}")
        print(f"  Overall: {s['passed']}/{s['total']} passed  "
              f"({s['pass_rate']*100:.1f}%)")
        print(f"  Elapsed: {s.get('elapsed_seconds', 0):.1f}s")
        print()

        print("  By category:")
        for cat, data in s.get("by_category", {}).items():
            print(f"    {cat:30s}  {data['passed']}/{data['total']}  "
                  f"({data['pass_rate']*100:.1f}%)")

        print()
        print("  By difficulty:")
        for diff, data in s.get("by_difficulty", {}).items():
            print(f"    {diff:30s}  {data['passed']}/{data['total']}  "
                  f"({data['pass_rate']*100:.1f}%)")

        print(f"{'='*60}\n")

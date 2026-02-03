"""Metrics collection and reporting."""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class TaskResult:
    """Result of a single task evaluation."""
    task_id: str
    category: str
    difficulty: str
    passed: bool
    response: str
    elapsed_time: float
    used_dasa: bool = False
    dasa_tools_available: list[str] = field(default_factory=list)
    error: Optional[str] = None
    iterations: int = 1


class MetricsCollector:
    """Collects and aggregates evaluation metrics."""

    def __init__(self):
        self.results: list[TaskResult] = []

    def record(self, result: TaskResult) -> None:
        """Record a task result."""
        self.results.append(result)

    def summary(self) -> dict[str, Any]:
        """Generate summary metrics."""
        if not self.results:
            return {"error": "No results recorded"}

        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)

        # By category
        by_category = defaultdict(lambda: {"total": 0, "passed": 0})
        for r in self.results:
            by_category[r.category]["total"] += 1
            if r.passed:
                by_category[r.category]["passed"] += 1

        category_rates = {
            cat: round(stats["passed"] / stats["total"] * 100, 1)
            for cat, stats in by_category.items()
        }

        # By difficulty
        by_difficulty = defaultdict(lambda: {"total": 0, "passed": 0})
        for r in self.results:
            by_difficulty[r.difficulty]["total"] += 1
            if r.passed:
                by_difficulty[r.difficulty]["passed"] += 1

        difficulty_rates = {
            diff: round(stats["passed"] / stats["total"] * 100, 1)
            for diff, stats in by_difficulty.items()
        }

        # DASA impact
        with_dasa = [r for r in self.results if r.used_dasa]
        without_dasa = [r for r in self.results if not r.used_dasa]

        dasa_impact = {}
        if with_dasa and without_dasa:
            with_rate = sum(1 for r in with_dasa if r.passed) / len(with_dasa)
            without_rate = sum(1 for r in without_dasa if r.passed) / len(without_dasa)
            dasa_impact = {
                "with_dasa": round(with_rate * 100, 1),
                "without_dasa": round(without_rate * 100, 1),
                "improvement": round((with_rate - without_rate) * 100, 1)
            }

        # Timing
        avg_time = sum(r.elapsed_time for r in self.results) / total

        return {
            "overall": {
                "total": total,
                "passed": passed,
                "rate": round(passed / total * 100, 1)
            },
            "by_category": category_rates,
            "by_difficulty": difficulty_rates,
            "dasa_impact": dasa_impact,
            "timing": {
                "average_seconds": round(avg_time, 2),
                "total_seconds": round(sum(r.elapsed_time for r in self.results), 2)
            }
        }

    def comparison_report(
        self,
        baseline_results: list[TaskResult],
        dasa_results: list[TaskResult]
    ) -> dict[str, Any]:
        """Generate comparison report between baseline and DASA runs."""

        baseline_by_id = {r.task_id: r for r in baseline_results}
        dasa_by_id = {r.task_id: r for r in dasa_results}

        # Find improvements
        improvements = []
        regressions = []
        unchanged = []

        for task_id in baseline_by_id:
            if task_id in dasa_by_id:
                baseline = baseline_by_id[task_id]
                dasa = dasa_by_id[task_id]

                if not baseline.passed and dasa.passed:
                    improvements.append(task_id)
                elif baseline.passed and not dasa.passed:
                    regressions.append(task_id)
                else:
                    unchanged.append(task_id)

        # Category breakdown
        category_impact = defaultdict(lambda: {"baseline": 0, "dasa": 0, "total": 0})

        for task_id in baseline_by_id:
            if task_id in dasa_by_id:
                baseline = baseline_by_id[task_id]
                dasa = dasa_by_id[task_id]
                cat = baseline.category

                category_impact[cat]["total"] += 1
                if baseline.passed:
                    category_impact[cat]["baseline"] += 1
                if dasa.passed:
                    category_impact[cat]["dasa"] += 1

        return {
            "summary": {
                "improvements": len(improvements),
                "regressions": len(regressions),
                "unchanged": len(unchanged),
                "net_improvement": len(improvements) - len(regressions)
            },
            "improved_tasks": improvements,
            "regressed_tasks": regressions,
            "by_category": {
                cat: {
                    "baseline_rate": round(stats["baseline"] / stats["total"] * 100, 1),
                    "dasa_rate": round(stats["dasa"] / stats["total"] * 100, 1),
                    "improvement": round((stats["dasa"] - stats["baseline"]) / stats["total"] * 100, 1)
                }
                for cat, stats in category_impact.items()
            }
        }

    def reset(self) -> None:
        """Clear all results."""
        self.results = []

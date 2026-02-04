"""Evaluation task runner."""

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from .checker import TaskChecker
from .metrics import MetricsCollector, TaskResult


@dataclass
class Task:
    """Represents an evaluation task."""
    id: str
    category: str
    difficulty: str
    notebook: str
    prompt: str
    expected_answer: Any
    check_type: str
    dasa_tools_helpful: list[str] = field(default_factory=list)
    baseline_expected_pass: bool = False
    target_cell: Optional[int] = None

    @classmethod
    def from_json(cls, path: Path) -> "Task":
        """Load task from JSON file."""
        with open(path) as f:
            data = json.load(f)

        return cls(
            id=data["id"],
            category=data["category"],
            difficulty=data["difficulty"],
            notebook=data["notebook"],
            prompt=data["prompt"],
            expected_answer=data.get("expected_answer") or data.get("expected_issues") or data.get("expected_fixes"),
            check_type=data["check_type"],
            dasa_tools_helpful=data.get("dasa_tools_helpful", []),
            baseline_expected_pass=data.get("baseline_expected_pass", False),
            target_cell=data.get("target_cell")
        )


class EvalRunner:
    """Runs evaluation tasks and collects results."""

    def __init__(
        self,
        tasks_dir: Path,
        notebooks_dir: Path,
        results_dir: Path
    ):
        self.tasks_dir = Path(tasks_dir)
        self.notebooks_dir = Path(notebooks_dir)
        self.results_dir = Path(results_dir)
        self.checker = TaskChecker()
        self.metrics = MetricsCollector()

    def load_tasks(self) -> list[Task]:
        """Load all tasks from the tasks directory."""
        tasks = []
        for category_dir in self.tasks_dir.iterdir():
            if category_dir.is_dir():
                for task_file in category_dir.glob("*.json"):
                    tasks.append(Task.from_json(task_file))
        return sorted(tasks, key=lambda t: t.id)

    def run_task(
        self,
        task: Task,
        agent_response: str,
        notebook_after: Optional[Path] = None,
        use_dasa: bool = False
    ) -> TaskResult:
        """Run a single task and check the result."""
        start_time = time.time()

        # Check the response
        passed = self.checker.check(
            task=task,
            response=agent_response,
            notebook_path=notebook_after
        )

        elapsed = time.time() - start_time

        result = TaskResult(
            task_id=task.id,
            category=task.category,
            difficulty=task.difficulty,
            passed=passed,
            response=agent_response,
            elapsed_time=elapsed,
            used_dasa=use_dasa,
            dasa_tools_available=task.dasa_tools_helpful
        )

        self.metrics.record(result)
        return result

    def run_all(
        self,
        agent_fn,
        use_dasa: bool = False
    ) -> dict[str, Any]:
        """Run all tasks with the given agent function.

        Args:
            agent_fn: Function that takes (task, notebook_path, use_dasa) and returns response
            use_dasa: Whether DASA tools are available

        Returns:
            Summary metrics
        """
        tasks = self.load_tasks()

        for task in tasks:
            notebook_path = self.notebooks_dir / task.notebook

            # Get agent response
            response = agent_fn(task, notebook_path, use_dasa)

            # Run task
            self.run_task(
                task=task,
                agent_response=response,
                use_dasa=use_dasa
            )

        return self.metrics.summary()

    def save_results(self, filename: str = "results.json") -> Path:
        """Save results to file."""
        output_path = self.results_dir / filename

        with open(output_path, "w") as f:
            json.dump({
                "summary": self.metrics.summary(),
                "results": [r.__dict__ for r in self.metrics.results]
            }, f, indent=2)

        return output_path

"""Evaluation runner for the DASA eval harness.

This module orchestrates the full evaluation loop: loading tasks,
invoking the agent, checking results, and collecting metrics.

Usage::

    from eval.harness import EvalRunner, DummyAgent, MetricsCollector

    agent = DummyAgent()
    runner = EvalRunner(
        tasks_dir="eval/tasks",
        notebooks_dir="eval/notebooks",
        agent=agent,
    )
    collector = runner.run_all()
    collector.print_summary()
    collector.save("eval/results/run_001.json")
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .agent import AgentWrapper
from .checker import CheckerDispatch, CheckResult
from .metrics import MetricsCollector, TaskResult


class EvalRunner:
    """Load task definitions, run an agent on each, and collect metrics.

    Parameters
    ----------
    tasks_dir:
        Root directory containing category subdirectories with task JSON
        files (e.g. ``eval/tasks/data_understanding/DU-01.json``).
    notebooks_dir:
        Directory containing the evaluation notebooks referenced by
        task definitions.
    agent:
        An :class:`AgentWrapper` instance to evaluate.
    results_dir:
        Optional directory in which to persist results.
    """

    def __init__(
        self,
        tasks_dir: str | Path,
        notebooks_dir: str | Path,
        agent: AgentWrapper,
        results_dir: str | Path | None = None,
    ) -> None:
        self.tasks_dir = Path(tasks_dir)
        self.notebooks_dir = Path(notebooks_dir)
        self.agent = agent
        self.results_dir = Path(results_dir) if results_dir else None
        self.checker = CheckerDispatch()

    # ------------------------------------------------------------------
    # Task loading
    # ------------------------------------------------------------------

    def discover_tasks(self) -> list[dict[str, Any]]:
        """Recursively discover all ``*.json`` task files under :attr:`tasks_dir`.

        Returns
        -------
        list[dict]
            Parsed task definitions sorted by task id.
        """
        tasks: list[dict[str, Any]] = []
        for task_file in sorted(self.tasks_dir.rglob("*.json")):
            with open(task_file) as fh:
                task = json.load(fh)
            task["_source_file"] = str(task_file)
            tasks.append(task)
        tasks.sort(key=lambda t: t.get("id", ""))
        return tasks

    # ------------------------------------------------------------------
    # Single-task execution
    # ------------------------------------------------------------------

    def run_task(self, task: dict[str, Any]) -> TaskResult:
        """Run the agent on a single task and check the result.

        Parameters
        ----------
        task:
            A parsed task definition dict.

        Returns
        -------
        TaskResult
            The outcome of the evaluation.
        """
        task_id: str = task["id"]
        category: str = task["category"]
        difficulty: str = task.get("difficulty", "unknown")
        prompt: str = task["prompt"]
        notebook_name: str = task["notebook"]
        criteria: dict = task["success_criteria"]

        # Load the notebook
        nb_path = self.notebooks_dir / notebook_name
        if not nb_path.exists():
            return TaskResult(
                task_id=task_id,
                category=category,
                difficulty=difficulty,
                passed=False,
                message=f"Notebook not found: {nb_path}",
            )

        with open(nb_path) as fh:
            notebook = json.load(fh)

        # Build context from setup block
        context: dict[str, Any] = task.get("setup", {})
        context["notebook_path"] = str(nb_path)
        context["data_dir"] = str(self.notebooks_dir.parent / "data")

        # Run the agent
        t0 = time.time()
        try:
            modified_nb, response = self.agent.run(prompt, notebook, context=context)
        except Exception as exc:
            duration = time.time() - t0
            return TaskResult(
                task_id=task_id,
                category=category,
                difficulty=difficulty,
                passed=False,
                message=f"Agent raised an exception: {exc}",
                duration_seconds=duration,
                details={"exception": str(exc)},
            )
        duration = time.time() - t0

        # Check success criteria
        try:
            check: CheckResult = self.checker.check(response, modified_nb, criteria)
        except Exception as exc:
            return TaskResult(
                task_id=task_id,
                category=category,
                difficulty=difficulty,
                passed=False,
                message=f"Checker raised an exception: {exc}",
                duration_seconds=duration,
                details={"exception": str(exc)},
            )

        return TaskResult(
            task_id=task_id,
            category=category,
            difficulty=difficulty,
            passed=check.passed,
            message=check.message,
            duration_seconds=duration,
            details=check.details,
        )

    # ------------------------------------------------------------------
    # Full evaluation
    # ------------------------------------------------------------------

    def run_all(
        self,
        task_filter: str | None = None,
        category_filter: str | None = None,
    ) -> MetricsCollector:
        """Run the agent on all discovered tasks and return metrics.

        Parameters
        ----------
        task_filter:
            If provided, only run tasks whose id contains this substring.
        category_filter:
            If provided, only run tasks in this category.

        Returns
        -------
        MetricsCollector
            Populated collector with all results.
        """
        tasks = self.discover_tasks()
        collector = MetricsCollector(agent_name=self.agent.name)

        if task_filter:
            tasks = [t for t in tasks if task_filter in t["id"]]
        if category_filter:
            tasks = [t for t in tasks if t["category"] == category_filter]

        print(f"Running {len(tasks)} tasks with agent '{self.agent.name}'...")
        print()

        for i, task in enumerate(tasks, 1):
            tid = task["id"]
            print(f"  [{i}/{len(tasks)}] {tid}: {task['name']}  ", end="", flush=True)

            result = self.run_task(task)
            collector.add_result(result)

            status = "PASS" if result.passed else "FAIL"
            print(f"  [{status}]  ({result.duration_seconds:.2f}s)")

        # Optionally save
        if self.results_dir:
            ts = time.strftime("%Y%m%d_%H%M%S")
            out_path = self.results_dir / f"run_{self.agent.name}_{ts}.json"
            collector.save(out_path)
            print(f"\nResults saved to {out_path}")

        return collector

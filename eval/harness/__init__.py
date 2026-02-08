"""DASA Evaluation Harness.

This package provides the infrastructure for evaluating Data Science Agent
capabilities across multiple task categories including data understanding,
bug fixing, visualization, state recovery, dependency reasoning, and
reproducibility.
"""

from .runner import EvalRunner
from .agent import AgentWrapper
from .checker import CheckerDispatch
from .metrics import MetricsCollector

__all__ = ["EvalRunner", "AgentWrapper", "CheckerDispatch", "MetricsCollector"]

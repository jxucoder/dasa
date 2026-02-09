"""DASA Evaluation Harness.

This package provides the infrastructure for evaluating Data Science Agent
capabilities across multiple task categories including data understanding,
bug fixing, visualization, state recovery, dependency reasoning, and
reproducibility.
"""

from .runner import EvalRunner
from .agent import AgentWrapper, DummyAgent
from .checker import CheckerDispatch
from .metrics import MetricsCollector
from .claude_agent import ClaudeVanillaAgent, ClaudeDasaAgent

__all__ = [
    "EvalRunner",
    "AgentWrapper",
    "DummyAgent",
    "CheckerDispatch",
    "MetricsCollector",
    "ClaudeVanillaAgent",
    "ClaudeDasaAgent",
]

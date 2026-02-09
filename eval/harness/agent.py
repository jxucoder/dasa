"""Agent wrapper interface for the DASA evaluation harness.

This module defines the abstract AgentWrapper class that must be implemented
by any agent being evaluated. It provides a standard interface for the eval
runner to interact with different agent implementations.
"""

from __future__ import annotations

import abc
import copy
import json
from pathlib import Path
from typing import Any


class AgentWrapper(abc.ABC):
    """Abstract base class for wrapping an LLM-based data-science agent.

    Subclasses must implement :meth:`run` which receives a task prompt and a
    notebook (as parsed JSON) and returns the modified notebook plus any
    textual response produced by the agent.

    Example usage::

        class MyAgent(AgentWrapper):
            def run(self, prompt, notebook, context=None):
                # ... call LLM, modify notebook ...
                return modified_notebook, response_text

        agent = MyAgent(name="my-agent-v1")
        result_nb, response = agent.run(prompt, nb_json)
    """

    def __init__(self, name: str = "base-agent", **kwargs: Any) -> None:
        """Initialise the agent wrapper.

        Parameters
        ----------
        name:
            Human-readable identifier for this agent variant.
        **kwargs:
            Additional configuration passed to the underlying agent.
        """
        self.name = name
        self.config = kwargs

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def run(
        self,
        prompt: str,
        notebook: dict,
        context: dict[str, Any] | None = None,
    ) -> tuple[dict, str]:
        """Execute the agent on a task.

        Parameters
        ----------
        prompt:
            The natural-language task description.
        notebook:
            A parsed Jupyter notebook (nbformat v4 dict).  The agent may
            modify this dict to fix code, add cells, etc.
        context:
            Optional additional context such as file paths, dataset
            metadata, or setup instructions.

        Returns
        -------
        tuple[dict, str]
            A 2-tuple of ``(modified_notebook, agent_response)`` where
            *modified_notebook* is the (potentially changed) notebook dict
            and *agent_response* is any free-text answer produced by the
            agent.
        """
        ...

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def load_notebook(self, path: str | Path) -> dict:
        """Load a notebook JSON file from disk.

        Parameters
        ----------
        path:
            Path to the ``.ipynb`` file.

        Returns
        -------
        dict
            Parsed notebook content.
        """
        with open(path) as fh:
            return json.load(fh)

    def save_notebook(self, notebook: dict, path: str | Path) -> None:
        """Write a notebook dict back to disk as JSON.

        Parameters
        ----------
        notebook:
            Notebook dict to serialise.
        path:
            Destination ``.ipynb`` file path.
        """
        with open(path, "w") as fh:
            json.dump(notebook, fh, indent=1)

    def clone_notebook(self, notebook: dict) -> dict:
        """Return a deep copy of a notebook so the original is not mutated.

        Parameters
        ----------
        notebook:
            Notebook dict to clone.

        Returns
        -------
        dict
            Independent deep copy.
        """
        return copy.deepcopy(notebook)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r})"


class DummyAgent(AgentWrapper):
    """A no-op agent used for testing the harness itself.

    Returns the notebook unmodified and an empty response string.
    """

    def __init__(self) -> None:
        super().__init__(name="dummy-agent")

    def run(
        self,
        prompt: str,
        notebook: dict,
        context: dict[str, Any] | None = None,
    ) -> tuple[dict, str]:
        """Return the notebook unchanged with an empty response."""
        return self.clone_notebook(notebook), ""

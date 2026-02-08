"""Abstract notebook adapter."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Cell:
    """Represents a notebook cell."""
    index: int
    cell_type: str  # "code" or "markdown"
    source: str
    outputs: list = field(default_factory=list)
    execution_count: Optional[int] = None


class NotebookAdapter(ABC):
    """Read/write/modify notebooks regardless of format."""

    @abstractmethod
    def load(self, path: str) -> None: ...

    @abstractmethod
    def save(self, path: str | None = None) -> None: ...

    @property
    @abstractmethod
    def cells(self) -> list[Cell]: ...

    @property
    def code_cells(self) -> list[Cell]:
        """Return only code cells."""
        return [c for c in self.cells if c.cell_type == "code"]

    @property
    def execution_order(self) -> list[int]:
        """Return cell indices sorted by execution order."""
        executed = [c for c in self.code_cells if c.execution_count is not None]
        return [c.index for c in sorted(executed, key=lambda c: c.execution_count)]

    @abstractmethod
    def get_cell(self, index: int) -> Cell: ...

    @abstractmethod
    def update_cell(self, index: int, source: str) -> None: ...

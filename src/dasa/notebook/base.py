"""Abstract notebook adapter interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Cell:
    """Represents a notebook cell."""
    index: int
    cell_type: str  # "code", "markdown", "raw"
    source: str
    outputs: list[dict[str, Any]] = field(default_factory=list)
    execution_count: Optional[int] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_code(self) -> bool:
        return self.cell_type == "code"

    @property
    def preview(self) -> str:
        """First line of source, truncated."""
        first_line = self.source.split('\n')[0]
        return first_line[:50] + ('...' if len(first_line) > 50 else '')


class NotebookAdapter(ABC):
    """Abstract interface for notebook formats."""

    @abstractmethod
    def load(self, path: str) -> None:
        """Load notebook from file."""
        pass

    @abstractmethod
    def save(self, path: Optional[str] = None) -> None:
        """Save notebook to file."""
        pass

    @property
    @abstractmethod
    def cells(self) -> list[Cell]:
        """Get all cells."""
        pass

    @property
    def code_cells(self) -> list[Cell]:
        """Get only code cells."""
        return [c for c in self.cells if c.is_code]

    @abstractmethod
    def add_cell(
        self,
        source: str,
        cell_type: str = "code",
        index: Optional[int] = None
    ) -> Cell:
        """Add a new cell."""
        pass

    @abstractmethod
    def update_cell(self, index: int, source: str) -> None:
        """Update cell source."""
        pass

    @abstractmethod
    def delete_cell(self, index: int) -> None:
        """Delete a cell."""
        pass

    @abstractmethod
    def get_cell(self, index: int) -> Cell:
        """Get cell by index."""
        pass

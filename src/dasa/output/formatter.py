"""Output formatting utilities."""

import json
from typing import Any

from rich.console import Console
from rich.table import Table


console = Console()


def format_json(data: Any) -> str:
    """Format data as JSON string."""
    return json.dumps(data, indent=2, default=str)


def print_json(data: Any) -> None:
    """Print data as formatted JSON."""
    console.print(format_json(data))


def create_table(title: str, columns: list[str]) -> Table:
    """Create a Rich table with given columns."""
    table = Table(title=title)
    for col in columns:
        table.add_column(col)
    return table

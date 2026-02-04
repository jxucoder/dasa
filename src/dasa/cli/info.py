"""Info command implementation."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from dasa.notebook.jupyter import JupyterAdapter
from dasa.analysis.parser import parse_cell
from dasa.output.formatter import format_bytes

console = Console()


def info(
    notebook: str = typer.Argument(..., help="Path to notebook"),
    format_output: str = typer.Option("text", "--format", "-f", help="Output format: text, json"),
) -> None:
    """Show notebook metadata and summary."""

    path = Path(notebook)

    if not path.exists():
        console.print(f"[red]Notebook not found: {notebook}[/red]")
        raise typer.Exit(1)

    adapter = JupyterAdapter(notebook)

    # Gather info
    stat = path.stat()

    # Count cells by type
    code_cells = sum(1 for c in adapter.cells if c.cell_type == "code")
    markdown_cells = sum(1 for c in adapter.cells if c.cell_type == "markdown")
    raw_cells = sum(1 for c in adapter.cells if c.cell_type == "raw")

    # Extract imports
    imports = set()
    for cell in adapter.code_cells:
        analysis = parse_cell(cell.source)
        imports.update(analysis.imports)

    # Filter to likely external packages
    stdlib = {'os', 'sys', 'json', 'datetime', 'time', 'math', 're', 'collections',
              'itertools', 'functools', 'pathlib', 'typing', 'dataclasses', 'abc',
              'copy', 'random', 'hashlib', 'io', 'csv', 'ast', 'pickle'}
    external_imports = sorted([i for i in imports if i not in stdlib])

    # Build info dict
    info_data = {
        "name": path.name,
        "path": str(path.absolute()),
        "format": "Jupyter (nbformat 4)",
        "kernel": adapter.kernel_spec,
        "cells": {
            "total": len(adapter.cells),
            "code": code_cells,
            "markdown": markdown_cells,
            "raw": raw_cells
        },
        "size_bytes": stat.st_size,
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "packages": external_imports
    }

    if format_output == "json":
        console.print(json.dumps(info_data, indent=2))
        return

    # Text output
    console.print(f"\n[bold]Notebook: {path.name}[/bold]\n")
    console.print(f"  Path: {path.absolute()}")
    console.print(f"  Format: Jupyter (nbformat 4)")
    console.print(f"  Kernel: {adapter.kernel_spec or 'python3'}")
    console.print(f"  Cells: {len(adapter.cells)} ({code_cells} code, {markdown_cells} markdown)")
    console.print()
    console.print(f"  Size: {format_bytes(stat.st_size)}")
    console.print(f"  Modified: {datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')}")

    if external_imports:
        console.print()
        console.print(f"  [bold]Packages imported:[/bold]")
        console.print(f"    {', '.join(external_imports[:10])}")
        if len(external_imports) > 10:
            console.print(f"    ... and {len(external_imports) - 10} more")

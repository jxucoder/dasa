"""Cells command implementation."""

import json
from typing import Optional

import typer
from rich.console import Console

from dasa.notebook.jupyter import JupyterAdapter
from dasa.analysis.parser import parse_cell
from dasa.cli.stale import load_state, hash_cell

console = Console()


def cells(
    notebook: str = typer.Argument(..., help="Path to notebook"),
    code_only: bool = typer.Option(False, "--code", "-c", help="Show only code cells"),
    show_source: bool = typer.Option(False, "--source", "-s", help="Show full source"),
    format_output: str = typer.Option("text", "--format", "-f", help="Output format: text, json"),
) -> None:
    """List all cells with previews and metadata."""

    adapter = JupyterAdapter(notebook)
    state = load_state(notebook)
    saved_hashes = state.get("cell_hashes", {})

    cells_data = []

    for cell in adapter.cells:
        if code_only and cell.cell_type != "code":
            continue

        cell_info = {
            "index": cell.index,
            "type": cell.cell_type,
            "lines": len(cell.source.split('\n')),
            "preview": cell.preview,
            "execution_count": cell.execution_count
        }

        # For code cells, add analysis
        if cell.cell_type == "code":
            analysis = parse_cell(cell.source)
            cell_info["defines"] = list(analysis.definitions)[:5]

            # Check staleness
            current_hash = hash_cell(cell.source)
            saved_hash = saved_hashes.get(str(cell.index))
            cell_info["stale"] = saved_hash is not None and saved_hash != current_hash

        if show_source:
            cell_info["source"] = cell.source

        cells_data.append(cell_info)

    if format_output == "json":
        console.print(json.dumps(cells_data, indent=2))
        return

    # Text output
    console.print(f"\n[bold]Cells in notebook ({len(cells_data)} total)[/bold]\n")

    for c in cells_data:
        # Build status markers
        markers = []
        if c.get("stale"):
            markers.append("[yellow]STALE[/yellow]")
        if c.get("execution_count") is None and c["type"] == "code":
            markers.append("[dim]not run[/dim]")

        marker_str = f" {' '.join(markers)}" if markers else ""

        # Cell header
        if c["type"] == "code":
            lines_str = f"({c['lines']} lines)"
            defines = c.get("defines", [])
            defines_str = f" - defines: {', '.join(defines[:3])}" if defines else ""
            console.print(f"[bold][{c['index']}][/bold] code {lines_str}{defines_str}{marker_str}")
        else:
            console.print(f"[bold][{c['index']}][/bold] {c['type']}{marker_str}")

        # Preview
        if show_source:
            for line in c.get("source", "").split('\n')[:10]:
                console.print(f"    {line}")
            if c.get("lines", 0) > 10:
                console.print(f"    [dim]... ({c['lines'] - 10} more lines)[/dim]")
        else:
            console.print(f"    {c['preview']}")

        console.print()

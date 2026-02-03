"""Deps command implementation."""

import json
from typing import Optional

import typer
from rich.console import Console

from dasa.notebook.jupyter import JupyterAdapter
from dasa.analysis.deps import DependencyAnalyzer, DependencyGraph

console = Console()


def deps(
    notebook: str = typer.Argument(..., help="Path to notebook"),
    cell: Optional[int] = typer.Option(None, "--cell", "-c", help="Show impact of modifying this cell"),
    format_output: str = typer.Option("text", "--format", "-f", help="Output format: text, json, dot"),
) -> None:
    """Analyze cell dependencies in a notebook."""

    adapter = JupyterAdapter(notebook)
    analyzer = DependencyAnalyzer()
    graph = analyzer.build_graph(adapter)

    if format_output == "json":
        data = {
            "cells": [
                {
                    "index": node.index,
                    "preview": node.preview,
                    "definitions": list(node.definitions),
                    "references": list(node.references),
                    "upstream": list(node.upstream),
                    "downstream": list(node.downstream)
                }
                for node in graph.nodes.values()
            ]
        }
        if cell is not None:
            data["impact"] = {
                "cell": cell,
                "affected": graph.get_downstream(cell)
            }
        console.print(json.dumps(data, indent=2))
        return

    # Text output
    if cell is not None:
        # Show impact of modifying a specific cell
        _show_cell_impact(graph, cell)
    else:
        # Show full dependency graph
        _show_full_graph(graph)


def _show_full_graph(graph: DependencyGraph) -> None:
    """Show full dependency graph."""

    console.print("\n[bold]Dependency Graph[/bold]\n")

    for idx in sorted(graph.nodes.keys()):
        node = graph.nodes[idx]

        # Cell header
        defs = ", ".join(sorted(node.definitions)[:5])
        defs_str = f" - defines: {defs}" if defs else ""

        if not node.downstream:
            terminal = " [dim][TERMINAL][/dim]"
        else:
            terminal = ""

        console.print(f"[bold]Cell {idx}[/bold] ({node.preview}){defs_str}{terminal}")

        # Downstream
        if node.downstream:
            downstream = ", ".join(f"Cell {i}" for i in sorted(node.downstream))
            console.print(f"  --> {downstream}")

        console.print()


def _show_cell_impact(graph: DependencyGraph, cell_index: int) -> None:
    """Show impact of modifying a cell."""

    if cell_index not in graph.nodes:
        console.print(f"[red]Cell {cell_index} not found[/red]")
        raise typer.Exit(1)

    node = graph.nodes[cell_index]
    affected = graph.get_downstream(cell_index)

    console.print(f"\n[bold]If you modify Cell {cell_index}:[/bold]")
    console.print(f"  Preview: {node.preview}")
    console.print(f"  Defines: {', '.join(sorted(node.definitions))}")
    console.print()

    if affected:
        console.print("[bold]Cells that need re-run:[/bold]")
        for idx in affected:
            affected_node = graph.nodes[idx]
            # Find which variables connect them
            shared = node.definitions & affected_node.references
            via = f" (uses: {', '.join(shared)})" if shared else ""
            console.print(f"  -> Cell {idx}{via}")

        console.print(f"\n[bold]Total:[/bold] {len(affected)} cells affected")
    else:
        console.print("[green]No downstream dependencies - safe to modify[/green]")

"""Edit command implementation."""

import ast
import difflib
from typing import Optional

import typer
from rich.console import Console

from dasa.notebook.jupyter import JupyterAdapter
from dasa.analysis.deps import DependencyAnalyzer

console = Console()


def edit(
    notebook: str = typer.Argument(..., help="Path to notebook"),
    cell: int = typer.Option(..., "--cell", "-c", help="Cell index to edit"),
    code: str = typer.Option(..., "--code", help="New code content"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip dependency warning"),
) -> None:
    """Edit an existing cell's content."""

    adapter = JupyterAdapter(notebook)

    # Validate cell index
    if cell < 0 or cell >= len(adapter.cells):
        console.print(f"[red]Cell {cell} not found (notebook has {len(adapter.cells)} cells)[/red]")
        raise typer.Exit(1)

    target_cell = adapter.get_cell(cell)

    if target_cell.cell_type != "code":
        console.print(f"[red]Cell {cell} is a {target_cell.cell_type} cell, not a code cell[/red]")
        raise typer.Exit(1)

    # Validate Python syntax
    try:
        ast.parse(code)
    except SyntaxError as e:
        console.print(f"[red]Syntax error in new code: {e}[/red]")
        raise typer.Exit(1)

    old_code = target_cell.source

    # Check dependencies
    dep_analyzer = DependencyAnalyzer()
    graph = dep_analyzer.build_graph(adapter)
    downstream = graph.get_downstream(cell)

    if downstream and not force:
        console.print(f"\n[yellow]Warning: Cell {cell} has downstream dependents:[/yellow]")
        for idx in downstream:
            node = graph.nodes[idx]
            console.print(f"  - Cell {idx}: {node.preview}")
        console.print()

    # Show diff
    console.print("[bold]Changes:[/bold]")
    diff = difflib.unified_diff(
        old_code.splitlines(keepends=True),
        code.splitlines(keepends=True),
        fromfile="original",
        tofile="modified",
        lineterm=""
    )

    for line in diff:
        if line.startswith('+') and not line.startswith('+++'):
            console.print(f"[green]{line.rstrip()}[/green]")
        elif line.startswith('-') and not line.startswith('---'):
            console.print(f"[red]{line.rstrip()}[/red]")
        else:
            console.print(line.rstrip())

    # Apply edit
    adapter.update_cell(cell, code)
    adapter.save()

    console.print(f"\n[green]Cell {cell} updated[/green]")

    if downstream:
        console.print(f"[yellow]Remember to re-run cells: {', '.join(str(i) for i in downstream)}[/yellow]")

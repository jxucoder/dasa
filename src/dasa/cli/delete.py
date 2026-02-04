"""Delete command implementation."""

from typing import Optional

import typer
from rich.console import Console

from dasa.notebook.jupyter import JupyterAdapter
from dasa.analysis.deps import DependencyAnalyzer

console = Console()


def delete(
    notebook: str = typer.Argument(..., help="Path to notebook"),
    cell: int = typer.Option(..., "--cell", "-c", help="Cell index to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Delete a cell from the notebook."""

    adapter = JupyterAdapter(notebook)

    # Validate cell index
    if cell < 0 or cell >= len(adapter.cells):
        console.print(f"[red]Cell {cell} not found (notebook has {len(adapter.cells)} cells)[/red]")
        raise typer.Exit(1)

    target_cell = adapter.get_cell(cell)

    # Check dependencies
    dep_analyzer = DependencyAnalyzer()
    graph = dep_analyzer.build_graph(adapter)

    if cell in graph.nodes:
        node = graph.nodes[cell]
        downstream = graph.get_downstream(cell)

        if downstream and not force:
            console.print(f"\n[yellow]Warning: Cell {cell} defines variables used elsewhere:[/yellow]")

            for var in node.definitions:
                # Find which downstream cells use this var
                using_cells = []
                for d_idx in downstream:
                    d_node = graph.nodes.get(d_idx)
                    if d_node and var in d_node.references:
                        using_cells.append(d_idx)
                if using_cells:
                    console.print(f"  - {var} (used in Cell {', '.join(str(c) for c in using_cells)})")

            console.print()
            confirm = typer.confirm("Delete anyway?")
            if not confirm:
                console.print("[dim]Cancelled[/dim]")
                raise typer.Exit(0)

    # Show what we're deleting
    console.print(f"\n[bold]Deleting Cell {cell}:[/bold]")
    console.print(f"  Type: {target_cell.cell_type}")
    console.print(f"  Preview: {target_cell.preview}")

    # Delete the cell
    adapter.delete_cell(cell)
    adapter.save()

    console.print(f"\n[green]Cell {cell} deleted[/green]")
    console.print(f"[dim]Note: Cell indices have been renumbered[/dim]")

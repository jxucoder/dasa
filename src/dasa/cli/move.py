"""Move command implementation."""

from typing import Optional

import typer
from rich.console import Console

from dasa.notebook.jupyter import JupyterAdapter
from dasa.analysis.deps import DependencyAnalyzer
from dasa.analysis.parser import parse_cell

console = Console()


def move(
    notebook: str = typer.Argument(..., help="Path to notebook"),
    cell: int = typer.Option(..., "--cell", "-c", help="Cell index to move"),
    to: int = typer.Option(..., "--to", "-t", help="Target position"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip dependency check"),
) -> None:
    """Move a cell to a different position."""

    adapter = JupyterAdapter(notebook)
    num_cells = len(adapter.cells)

    # Validate cell indices
    if cell < 0 or cell >= num_cells:
        console.print(f"[red]Cell {cell} not found (notebook has {num_cells} cells)[/red]")
        raise typer.Exit(1)

    if to < 0 or to >= num_cells:
        console.print(f"[red]Invalid target position: {to}[/red]")
        raise typer.Exit(1)

    if cell == to:
        console.print("[dim]Cell is already at that position[/dim]")
        return

    target_cell = adapter.get_cell(cell)

    # Check if move creates dependency issues
    if not force:
        issues = _check_move_safety(adapter, cell, to)
        if issues:
            console.print(f"\n[yellow]Warning: This move may cause issues:[/yellow]")
            for issue in issues:
                console.print(f"  - {issue}")
            console.print()
            confirm = typer.confirm("Move anyway?")
            if not confirm:
                console.print("[dim]Cancelled[/dim]")
                raise typer.Exit(0)

    # Perform the move
    # Delete from old position and insert at new position
    cell_source = target_cell.source
    cell_type = target_cell.cell_type

    adapter.delete_cell(cell)

    # Adjust target if we deleted a cell before it
    adjusted_to = to if cell > to else to - 1

    adapter.add_cell(cell_source, cell_type=cell_type, index=adjusted_to)
    adapter.save()

    console.print(f"[green]Moved Cell {cell} to position {to}[/green]")

    # Show new order
    console.print(f"\n[bold]New cell order:[/bold]")
    for i, c in enumerate(adapter.cells[:8]):
        marker = "[bold]*[/bold]" if i == adjusted_to else " "
        console.print(f"  {marker}[{i}] {c.cell_type}: {c.source[:40]}...")

    if num_cells > 8:
        console.print(f"  ... ({num_cells - 8} more cells)")


def _check_move_safety(adapter: JupyterAdapter, from_idx: int, to_idx: int) -> list[str]:
    """Check if a move would create dependency issues."""

    issues = []

    # Parse all cells
    cells_analysis = {}
    for c in adapter.code_cells:
        cells_analysis[c.index] = parse_cell(c.source)

    moving_cell = adapter.get_cell(from_idx)
    if moving_cell.cell_type != "code":
        return issues

    moving_analysis = cells_analysis.get(from_idx)
    if not moving_analysis:
        return issues

    # What the moving cell defines and references
    moving_defs = moving_analysis.definitions
    moving_refs = moving_analysis.references

    if to_idx < from_idx:
        # Moving up - check if cell references things defined between to and from
        for idx in range(to_idx, from_idx):
            cell = adapter.get_cell(idx)
            if cell.cell_type != "code":
                continue
            analysis = cells_analysis.get(idx)
            if analysis:
                # If moving cell references something this cell defines
                conflicts = moving_refs & analysis.definitions
                if conflicts:
                    issues.append(
                        f"Cell {from_idx} uses '{list(conflicts)[0]}' defined in Cell {idx}"
                    )
    else:
        # Moving down - check if cells between from and to reference what we define
        for idx in range(from_idx + 1, to_idx + 1):
            cell = adapter.get_cell(idx)
            if cell.cell_type != "code":
                continue
            analysis = cells_analysis.get(idx)
            if analysis:
                # If this cell references something the moving cell defines
                conflicts = analysis.references & moving_defs
                if conflicts:
                    issues.append(
                        f"Cell {idx} uses '{list(conflicts)[0]}' defined in Cell {from_idx}"
                    )

    return issues

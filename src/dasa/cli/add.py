"""Add command implementation."""

import ast
from typing import Optional

import typer
from rich.console import Console

from dasa.notebook.jupyter import JupyterAdapter

console = Console()


def add(
    notebook: str = typer.Argument(..., help="Path to notebook"),
    code: Optional[str] = typer.Option(None, "--code", "-c", help="Code to add"),
    markdown: Optional[str] = typer.Option(None, "--markdown", "-m", help="Markdown content"),
    at: Optional[int] = typer.Option(None, "--at", help="Insert at position"),
    after: Optional[int] = typer.Option(None, "--after", help="Insert after cell"),
    before: Optional[int] = typer.Option(None, "--before", help="Insert before cell"),
) -> None:
    """Add a new cell to the notebook."""

    if not code and not markdown:
        console.print("[red]Error: Must specify --code or --markdown[/red]")
        raise typer.Exit(1)

    if code and markdown:
        console.print("[red]Error: Cannot specify both --code and --markdown[/red]")
        raise typer.Exit(1)

    # Determine cell type and content
    if code:
        cell_type = "code"
        content = code

        # Validate Python syntax
        try:
            ast.parse(content)
        except SyntaxError as e:
            console.print(f"[red]Syntax error in code: {e}[/red]")
            raise typer.Exit(1)
    else:
        cell_type = "markdown"
        content = markdown

    adapter = JupyterAdapter(notebook)

    # Determine insertion position
    num_cells = len(adapter.cells)

    if at is not None:
        position = at
    elif after is not None:
        position = after + 1
    elif before is not None:
        position = before
    else:
        # Default: append at end
        position = num_cells

    # Validate position
    if position < 0 or position > num_cells:
        console.print(f"[red]Invalid position: {position} (notebook has {num_cells} cells)[/red]")
        raise typer.Exit(1)

    # Add the cell
    new_cell = adapter.add_cell(content, cell_type=cell_type, index=position)
    adapter.save()

    console.print(f"[green]Added {cell_type} cell at position {position}[/green]")

    # Show preview
    preview = content.split('\n')[0][:50]
    if len(content) > 50 or '\n' in content:
        preview += "..."
    console.print(f"  Content: {preview}")

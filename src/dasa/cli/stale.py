"""Stale command implementation."""

import hashlib
import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from dasa.notebook.jupyter import JupyterAdapter
from dasa.analysis.deps import DependencyAnalyzer

console = Console()


def get_dasa_dir(notebook_path: str) -> Path:
    """Get or create .dasa directory for state storage."""
    notebook = Path(notebook_path)
    dasa_dir = notebook.parent / ".dasa"
    dasa_dir.mkdir(exist_ok=True)
    return dasa_dir


def get_state_file(notebook_path: str) -> Path:
    """Get state file path for a notebook."""
    dasa_dir = get_dasa_dir(notebook_path)
    notebook_name = Path(notebook_path).stem
    return dasa_dir / f"{notebook_name}_state.json"


def hash_cell(source: str) -> str:
    """Hash cell source code."""
    return hashlib.md5(source.encode()).hexdigest()


def load_state(notebook_path: str) -> dict:
    """Load saved state from .dasa directory."""
    state_file = get_state_file(notebook_path)
    if state_file.exists():
        return json.loads(state_file.read_text())
    return {"cell_hashes": {}, "last_run": {}}


def save_state(notebook_path: str, state: dict) -> None:
    """Save state to .dasa directory."""
    state_file = get_state_file(notebook_path)
    state_file.write_text(json.dumps(state, indent=2))


def stale(
    notebook: str = typer.Argument(..., help="Path to notebook"),
    update: bool = typer.Option(False, "--update", "-u", help="Update state after checking"),
    format_output: str = typer.Option("text", "--format", "-f", help="Output format: text, json"),
) -> None:
    """Find cells with outdated outputs."""

    adapter = JupyterAdapter(notebook)
    state = load_state(notebook)

    # Build dependency graph
    dep_analyzer = DependencyAnalyzer()
    graph = dep_analyzer.build_graph(adapter)

    # Check each cell
    stale_cells: list[dict] = []
    up_to_date: list[int] = []
    current_hashes: dict[str, str] = {}

    for cell in adapter.code_cells:
        cell_id = str(cell.index)
        current_hash = hash_cell(cell.source)
        current_hashes[cell_id] = current_hash

        saved_hash = state.get("cell_hashes", {}).get(cell_id)

        if saved_hash is None:
            # Never tracked - assume stale if never executed
            if cell.execution_count is None:
                stale_cells.append({
                    "cell": cell.index,
                    "reason": "never executed",
                    "preview": cell.preview
                })
            else:
                up_to_date.append(cell.index)
        elif saved_hash != current_hash:
            # Code changed since last run
            stale_cells.append({
                "cell": cell.index,
                "reason": "code modified",
                "preview": cell.preview
            })

    # Propagate staleness through dependencies
    stale_indices = {s["cell"] for s in stale_cells}
    propagated: list[dict] = []

    for cell in adapter.code_cells:
        if cell.index in stale_indices:
            continue

        # Check if any upstream dependency is stale
        upstream = graph.get_upstream(cell.index)
        stale_upstream = [u for u in upstream if u in stale_indices]

        if stale_upstream:
            # Find which variables connect them
            node = graph.nodes[cell.index]
            stale_vars = []
            for u_idx in stale_upstream:
                u_node = graph.nodes.get(u_idx)
                if u_node:
                    shared = u_node.definitions & node.references
                    stale_vars.extend(shared)

            propagated.append({
                "cell": cell.index,
                "reason": f"depends on Cell {stale_upstream[0]}",
                "via": list(set(stale_vars))[:3],
                "preview": cell.preview
            })
            stale_indices.add(cell.index)

    all_stale = stale_cells + propagated
    up_to_date = [c.index for c in adapter.code_cells if c.index not in stale_indices]

    if format_output == "json":
        console.print(json.dumps({
            "stale": all_stale,
            "up_to_date": up_to_date
        }, indent=2))
    else:
        console.print("\n[bold]Cell Staleness Analysis[/bold]\n")

        if all_stale:
            console.print("[yellow]Stale cells (need re-run):[/yellow]")
            for s in all_stale:
                via = f" (via: {', '.join(s['via'])})" if s.get('via') else ""
                console.print(f"  [yellow]![/yellow] Cell {s['cell']}: {s['reason']}{via}")
                console.print(f"      {s['preview']}")
            console.print()

        if up_to_date:
            console.print("[green]Up to date:[/green]")
            console.print(f"  [green]OK[/green] Cells: {', '.join(str(i) for i in up_to_date)}")

    # Update state if requested
    if update:
        state["cell_hashes"] = current_hashes
        save_state(notebook, state)
        console.print("\n[dim]State updated[/dim]")

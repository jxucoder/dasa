"""Check command — combined notebook health report."""

import json

import typer
from rich.console import Console

from dasa.notebook.jupyter import JupyterAdapter
from dasa.analysis.state import StateAnalyzer
from dasa.analysis.deps import DependencyAnalyzer
from dasa.session.log import SessionLog

console = Console()


def check(
    notebook: str = typer.Argument(..., help="Path to notebook"),
    cell: int = typer.Option(None, "--cell", "-c", help="Show impact of modifying this cell"),
    format: str = typer.Option("text", "--format", "-f", help="Output format: text, json"),
) -> None:
    """Check notebook health: state, dependencies, staleness."""
    adapter = JupyterAdapter(notebook)

    # Run all analyses
    state_analyzer = StateAnalyzer()
    state_analysis = state_analyzer.analyze(adapter)

    dep_analyzer = DependencyAnalyzer()
    dep_graph = dep_analyzer.build_graph(adapter)

    if format == "json":
        data = {
            "notebook": notebook,
            "cell_count": len(adapter.cells),
            "state": state_analysis.to_dict(),
            "dependencies": dep_graph.to_dict(),
        }
        if cell is not None:
            data["impact"] = {
                "cell": cell,
                "downstream": dep_graph.get_downstream(cell),
            }
        console.print(json.dumps(data, indent=2))
        return

    # Text output
    console.print(f"\n[bold]Notebook:[/bold] {notebook} ({len(adapter.cells)} cells)\n")

    # State section
    _print_state_section(state_analysis)

    # Dependencies section
    _print_deps_section(dep_graph, cell)

    # Execution order section
    _print_execution_order(state_analysis)

    # Auto-log findings
    log = SessionLog()
    issue_count = len(state_analysis.issues)
    if issue_count:
        log.append("check", f"Found {issue_count} issues in {notebook}")
    else:
        log.append("check", f"{notebook} is consistent")

    # Exit with error code if inconsistent
    if not state_analysis.is_consistent:
        raise typer.Exit(1)


def _print_state_section(analysis) -> None:
    """Print state analysis section."""
    console.print("[bold]State:[/bold]")

    errors = [i for i in analysis.issues if i.severity == "error"]
    warnings = [i for i in analysis.issues if i.severity == "warning"]

    for issue in errors:
        cell_str = f"Cell {issue.cell_index}" if issue.cell_index >= 0 else "Notebook"
        console.print(f"  [red]X[/red] {cell_str}: {issue.message}")

    for issue in warnings:
        cell_str = f"Cell {issue.cell_index}" if issue.cell_index >= 0 else "Notebook"
        console.print(f"  [yellow]![/yellow] {cell_str}: {issue.message}")

    ok_count = max(0, len(analysis.correct_order) - len(errors) - len(warnings))
    if ok_count > 0:
        console.print(f"  [green]OK[/green] {ok_count} cells consistent")

    console.print()


def _print_deps_section(graph, target_cell=None) -> None:
    """Print dependency section."""
    console.print("[bold]Dependencies:[/bold]")

    for idx, node in sorted(graph.nodes.items()):
        if node.downstream:
            downstream_str = ", ".join(str(d) for d in sorted(node.downstream))
            console.print(f"  Cell {idx} ({node.label}) -> Cell {downstream_str}")

    if target_cell is not None and target_cell in graph.nodes:
        downstream = graph.get_downstream(target_cell)
        if downstream:
            downstream_str = ", ".join(str(d) for d in downstream)
            console.print(
                f"\n  If you modify Cell {target_cell}: "
                f"{len(downstream)} cells need re-run -> [{downstream_str}]"
            )
        else:
            console.print(f"\n  Cell {target_cell} has no downstream dependents")

    # Find dead code (no downstream dependents, not terminal)
    dead_cells = [
        idx for idx, node in graph.nodes.items()
        if not node.downstream and node.references  # has refs but nothing depends on it
    ]

    console.print()


def _print_execution_order(analysis) -> None:
    """Print execution order section."""
    if analysis.execution_order and analysis.execution_order != analysis.correct_order:
        actual_str = " -> ".join(f"[{i}]" for i in analysis.execution_order)
        correct_str = " -> ".join(f"[{i}]" for i in analysis.correct_order)
        console.print("[bold]Execution Order:[/bold]")
        console.print(f"  Actual:  {actual_str}  [yellow](out of order!)[/yellow]")
        console.print(f"  Correct: {correct_str}")
        console.print()

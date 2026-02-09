"""Check command — combined notebook health report."""

import json

import typer
from rich.console import Console

from dasa.notebook.loader import get_adapter
from dasa.notebook.kernel import DasaKernelManager
from dasa.analysis.state import StateAnalyzer
from dasa.analysis.deps import DependencyAnalyzer
from dasa.session.log import SessionLog
from dasa.session.state import StateTracker

console = Console()


def check(
    notebook: str = typer.Argument(..., help="Path to notebook"),
    cell: int = typer.Option(None, "--cell", "-c", help="Show impact of modifying this cell"),
    fix: bool = typer.Option(False, "--fix", help="Auto-fix: re-run stale and never-executed cells"),
    format: str = typer.Option("text", "--format", "-f", help="Output format: text, json"),
) -> None:
    """Check notebook health: state, dependencies, staleness."""
    adapter = get_adapter(notebook)

    # Run all analyses
    state_analyzer = StateAnalyzer()
    state_analysis = state_analyzer.analyze(adapter)

    dep_analyzer = DependencyAnalyzer()
    dep_graph = dep_analyzer.build_graph(adapter)

    if fix:
        _auto_fix(notebook, adapter, state_analysis, format)
        return

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


def _auto_fix(notebook: str, adapter, state_analysis, format: str) -> None:
    """Auto-fix by re-running stale and never-executed cells."""
    code_cells = adapter.code_cells

    # Find fixable cells: never-executed or stale
    tracker = StateTracker()
    cells_to_fix = []
    for c in code_cells:
        if c.execution_count is None:
            cells_to_fix.append(c)
        elif tracker.is_stale(notebook, c.index, c.source):
            cells_to_fix.append(c)

    if not cells_to_fix:
        console.print("[green]Nothing to fix — all cells are up to date.[/green]")
        return

    if format != "json":
        console.print(f"\n[bold]Fixing {len(cells_to_fix)} cells...[/bold]\n")

    kernel = DasaKernelManager()
    results = []

    try:
        kernel.start()

        # Replay all cells in order to build up state
        first_fix = min(c.index for c in cells_to_fix)
        for c in code_cells:
            if c.index < first_fix and c.execution_count is not None:
                kernel.execute(c.source, timeout=300)

        # Execute fixable cells
        for target_cell in cells_to_fix:
            result = kernel.execute(target_cell.source, timeout=300)
            cell_result = {
                "cell": target_cell.index,
                "success": result.success,
                "execution_time": result.execution_time,
            }

            if result.success:
                tracker.update_cell(notebook, target_cell.index, target_cell.source)
                if format != "json":
                    console.print(
                        f"  [green]Cell {target_cell.index}: OK[/green] "
                        f"({result.execution_time:.1f}s)"
                    )
            else:
                cell_result["error"] = f"{result.error_type}: {result.error}"
                if format != "json":
                    console.print(
                        f"  [red]Cell {target_cell.index}: FAILED[/red] "
                        f"({result.execution_time:.1f}s) — "
                        f"{result.error_type}: {result.error}"
                    )

            results.append(cell_result)

    finally:
        kernel.shutdown()

    if format == "json":
        console.print(json.dumps({"fixed": results}, indent=2))
    else:
        ok = sum(1 for r in results if r["success"])
        console.print(f"\n[bold]Fixed {ok}/{len(results)} cells.[/bold]\n")

    log = SessionLog()
    ok = sum(1 for r in results if r["success"])
    log.append("check", f"Auto-fixed {ok}/{len(results)} cells in {notebook}")

    if any(not r["success"] for r in results):
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

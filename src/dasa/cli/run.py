"""Run command — cell execution with rich error context."""

import json

import typer
from rich.console import Console

from dasa.notebook.loader import get_adapter
from dasa.notebook.kernel import DasaKernelManager
from dasa.analysis.error_context import build_error_context
from dasa.analysis.deps import DependencyAnalyzer
from dasa.session.log import SessionLog
from dasa.session.state import StateTracker

console = Console()


def run(
    notebook: str = typer.Argument(..., help="Path to notebook"),
    cell: int = typer.Option(None, "--cell", "-c", help="Run a single cell"),
    from_cell: int = typer.Option(None, "--from", help="Run from this cell to end"),
    to_cell: int = typer.Option(None, "--to", help="Run from start to this cell"),
    all_cells: bool = typer.Option(False, "--all", help="Run all cells"),
    stale: bool = typer.Option(False, "--stale", help="Run only stale cells"),
    stream: bool = typer.Option(False, "--stream", "-s", help="Stream output live as cells execute"),
    timeout: int = typer.Option(300, "--timeout", "-t", help="Timeout per cell in seconds"),
    format: str = typer.Option("text", "--format", "-f", help="Output format: text, json"),
) -> None:
    """Execute notebook cells with rich error context."""
    adapter = get_adapter(notebook)
    code_cells = adapter.code_cells

    # Determine which cells to run
    cells_to_run = _resolve_cells(code_cells, cell, from_cell, to_cell, all_cells, stale, notebook)

    if not cells_to_run:
        console.print("[yellow]No cells to run.[/yellow]")
        return

    # Build dependency info
    dep_analyzer = DependencyAnalyzer()
    dep_graph = dep_analyzer.build_graph(adapter)

    kernel = DasaKernelManager()
    log = SessionLog()
    state_tracker = StateTracker()
    results = []

    try:
        kernel.start()

        # Replay cells before the first target cell to restore state
        first_target = min(c.index for c in cells_to_run)
        for c in code_cells:
            if c.index < first_target and c.execution_count is not None:
                kernel.execute(c.source, timeout=timeout)

        # Execute target cells
        for target_cell in cells_to_run:
            if stream and format != "json":
                console.print(f"[bold]--- Cell {target_cell.index} ---[/bold]")
                gen = kernel.execute_streaming(target_cell.source, timeout=timeout)
                try:
                    while True:
                        stream_type, text = next(gen)
                        if stream_type == "stdout":
                            console.print(text, end="", highlight=False)
                        elif stream_type == "stderr":
                            console.print(f"[dim]{text}[/dim]", end="", highlight=False)
                        elif stream_type == "error":
                            console.print(f"[red]{text}[/red]")
                except StopIteration as e:
                    result = e.value
                console.print()  # newline after streaming
            else:
                result = kernel.execute(target_cell.source, timeout=timeout)

            cell_result = {
                "cell": target_cell.index,
                "success": result.success,
                "execution_time": result.execution_time,
            }

            if result.success:
                cell_result["stdout"] = result.stdout
                if result.result:
                    cell_result["result"] = result.result

                # Check for stale downstream cells
                downstream = dep_graph.get_downstream(target_cell.index)
                if downstream:
                    cell_result["stale_downstream"] = downstream

                # Update state tracking
                state_tracker.update_cell(notebook, target_cell.index, target_cell.source)

                if format != "json":
                    console.print(
                        f"[green]Running Cell {target_cell.index}... OK[/green] "
                        f"({result.execution_time:.1f}s)"
                    )
                    if result.stdout.strip():
                        console.print(f"\nOutput:\n  {result.stdout.strip()}")
                    if downstream:
                        ds_str = ", ".join(f"Cell {d}" for d in downstream)
                        console.print(
                            f"\n[yellow]! Downstream cells may be stale: {ds_str}[/yellow]"
                        )
                        console.print(
                            f"  Run `dasa run {notebook} --from {downstream[0]}` to update"
                        )

                log.append("run", f"Cell {target_cell.index} executed (success, {result.execution_time:.1f}s)")

            else:
                # Build rich error context
                error_ctx = build_error_context(
                    result.error_type or "Unknown",
                    result.error or "Unknown error",
                    target_cell.source,
                    result.traceback,
                    kernel,
                )
                cell_result["error"] = error_ctx

                if format != "json":
                    console.print(
                        f"[red]Running Cell {target_cell.index}... FAILED[/red] "
                        f"({result.execution_time:.1f}s)"
                    )
                    console.print(
                        f"\n[red]Error: {result.error_type}: {result.error}[/red]"
                    )
                    if error_ctx.get("error_line"):
                        line_info = error_ctx["error_line"]
                        console.print(
                            f"  Line {line_info['line_number']}: {line_info['content']}"
                        )
                    if error_ctx.get("available_columns"):
                        cols = ", ".join(error_ctx["available_columns"])
                        console.print(f"\nAvailable columns: {cols}")
                    if error_ctx.get("available_variables"):
                        # Show first 20 variables
                        vars_list = error_ctx["available_variables"][:20]
                        vars_str = ", ".join(vars_list)
                        console.print(f"\nAvailable variables: {vars_str}")
                    if error_ctx.get("suggestion"):
                        console.print(f"[cyan]Suggestion: {error_ctx['suggestion']}[/cyan]")

                log.append(
                    "run",
                    f"Cell {target_cell.index} failed: {result.error_type}: {result.error}",
                )

            results.append(cell_result)
            console.print()

        if format == "json":
            console.print(json.dumps(results, indent=2))

    finally:
        kernel.shutdown()

    # Exit with error if any cell failed
    if any(not r["success"] for r in results):
        raise typer.Exit(1)


def _resolve_cells(code_cells, cell, from_cell, to_cell, all_cells, stale_only, notebook):
    """Determine which cells to execute."""
    if cell is not None:
        return [c for c in code_cells if c.index == cell]

    if all_cells:
        return code_cells

    if from_cell is not None:
        return [c for c in code_cells if c.index >= from_cell]

    if to_cell is not None:
        return [c for c in code_cells if c.index <= to_cell]

    if stale_only:
        tracker = StateTracker()
        stale_indices = tracker.get_stale_cells(
            notebook,
            [(c.index, c.source) for c in code_cells],
        )
        return [c for c in code_cells if c.index in stale_indices]

    # Default: run all cells
    return code_cells

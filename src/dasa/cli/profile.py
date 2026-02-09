"""Profile command — data profiling."""

import json
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from dasa.notebook.loader import get_adapter
from dasa.notebook.kernel import DasaKernelManager
from dasa.analysis.profiler import Profiler, profile_csv
from dasa.session.log import SessionLog
from dasa.session.profiles import ProfileCache
from dasa.session.state import StateTracker

console = Console()


def _should_replay(cell, state_tracker: StateTracker, notebook: str) -> bool:
    """Check if a cell should be replayed to restore kernel state.

    A cell should be replayed if it was executed either:
    - In Jupyter/Colab (execution_count is set in .ipynb), OR
    - Via dasa run (tracked in state.json and code hasn't changed)
    """
    if cell.execution_count is not None:
        return True
    return state_tracker.was_executed_current(notebook, cell.index, cell.source)


def profile(
    notebook: str = typer.Argument(None, help="Path to notebook (.ipynb/.py)"),
    var: Optional[str] = typer.Option(None, "--var", "-v", help="Variable name to profile (omit to list all DataFrames)"),
    file: Optional[str] = typer.Option(None, "--file", help="Profile a CSV file directly (no kernel needed)"),
    format: str = typer.Option("text", "--format", "-f", help="Output format: text, json"),
) -> None:
    """Profile a DataFrame variable or CSV file.

    Without --var: lists all DataFrames in the notebook.
    With --var: profiles that specific variable.
    With --file: profiles a CSV directly (no kernel needed).
    """
    # CSV file profiling (no kernel needed)
    if file is not None:
        try:
            df_profile = profile_csv(file)
        except (FileNotFoundError, ValueError) as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)

        if format == "json":
            console.print(json.dumps(df_profile.to_dict(), indent=2))
        else:
            _print_profile(df_profile)

        # Auto-cache and log
        cache = ProfileCache()
        cache.save(df_profile.name, df_profile.to_dict())
        log = SessionLog()
        issues_str = ", ".join(df_profile.issues[:3]) if df_profile.issues else "none"
        log.append(
            "profile",
            f"Profiled CSV {file}. {df_profile.shape[0]:,} rows x {df_profile.shape[1]} cols. "
            f"Issues: {issues_str}",
        )
        return

    # Notebook-based profiling requires a notebook argument
    if notebook is None:
        console.print("[red]Error: provide a notebook path or --file for CSV profiling[/red]")
        raise typer.Exit(1)

    adapter = get_adapter(notebook)
    state_tracker = StateTracker()

    # Start kernel and replay executed cells
    kernel = DasaKernelManager()
    try:
        kernel.start()
    except Exception as e:
        console.print(f"[red]Error: Failed to start kernel: {e}[/red]")
        console.print("[dim]Is ipykernel installed? Try: pip install ipykernel[/dim]")
        raise typer.Exit(1)

    try:
        # Replay previously-executed cells to restore state
        # Checks BOTH notebook execution_count AND state.json
        for cell in adapter.code_cells:
            if _should_replay(cell, state_tracker, notebook):
                result = kernel.execute(cell.source, timeout=60)
                if not result.success:
                    console.print(
                        f"[yellow]Warning: Cell {cell.index} failed during replay: "
                        f"{result.error_type}: {result.error}[/yellow]"
                    )

        profiler = Profiler(kernel)

        if var is None:
            # Auto-discovery: list all DataFrames
            dataframes = profiler.list_dataframes()
            if not dataframes:
                console.print("[yellow]No DataFrames found in the notebook kernel.[/yellow]")
                return

            if format == "json":
                console.print(json.dumps(dataframes, indent=2))
            else:
                console.print(f"\n[bold]DataFrames in {notebook}:[/bold]\n")
                table = Table()
                table.add_column("Variable", style="cyan")
                table.add_column("Shape", style="green")
                table.add_column("Memory", style="white")
                for df_info in dataframes:
                    shape_str = f"{df_info['shape'][0]:,} x {df_info['shape'][1]}"
                    mem_str = f"{df_info['memory_mb']:.1f} MB"
                    table.add_row(df_info["name"], shape_str, mem_str)
                console.print(table)
                console.print(
                    "\n[dim]Use --var <name> to profile a specific DataFrame[/dim]\n"
                )

            log = SessionLog()
            names = ", ".join(d["name"] for d in dataframes)
            log.append("profile", f"Listed {len(dataframes)} DataFrames in {notebook}: {names}")
            return

        # Profile a specific variable
        try:
            df_profile = profiler.profile_dataframe(var)
        except RuntimeError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)

        # Output
        if format == "json":
            console.print(json.dumps(df_profile.to_dict(), indent=2))
        else:
            _print_profile(df_profile)

        # Auto-cache profile
        cache = ProfileCache()
        cache.save(var, df_profile.to_dict())

        # Auto-log
        log = SessionLog()
        issues_str = ", ".join(df_profile.issues[:3]) if df_profile.issues else "none"
        log.append(
            "profile",
            f"Profiled {var}. {df_profile.shape[0]:,} rows x {df_profile.shape[1]} cols. "
            f"Issues: {issues_str}",
        )

    finally:
        kernel.shutdown()


def _print_profile(profile) -> None:
    """Print profile as formatted text."""
    console.print(
        f"\n[bold]DataFrame: {profile.name}[/bold] "
        f"({profile.shape[0]:,} rows x {profile.shape[1]} columns)"
    )
    console.print(f"Memory: {profile.memory_bytes / 1024 / 1024:.1f} MB\n")

    table = Table()
    table.add_column("Column", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("Non-Null", style="white")
    table.add_column("Unique", style="white")
    table.add_column("Stats / Values", style="white")
    table.add_column("Issues", style="yellow")

    for col in profile.columns:
        non_null = f"{col.non_null_count:,} ({100 - col.null_percent:.0f}%)"
        unique = str(col.unique_count)

        # Stats
        stats_parts = []
        if col.min_val is not None:
            stats_parts.append(f"min={col.min_val:.4g}")
            stats_parts.append(f"max={col.max_val:.4g}")
            if col.mean_val is not None:
                stats_parts.append(f"mean={col.mean_val:.4g}")
        elif col.top_values:
            vals = ", ".join(f"'{v}'" for v in col.top_values[:4])
            stats_parts.append(vals)
        stats = ", ".join(stats_parts)

        # Issues
        issues = ", ".join(col.issues) if col.issues else ""

        table.add_row(col.name, col.dtype, non_null, unique, stats, issues)

    console.print(table)

    if profile.issues:
        console.print("\n[bold]Data Quality Issues:[/bold]")
        for issue in profile.issues:
            console.print(f"  [yellow]![/yellow] {issue}")
    console.print()

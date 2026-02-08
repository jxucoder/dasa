"""Profile command — data profiling."""

import json
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from dasa.notebook.jupyter import JupyterAdapter
from dasa.notebook.kernel import DasaKernelManager
from dasa.analysis.profiler import Profiler
from dasa.session.log import SessionLog
from dasa.session.profiles import ProfileCache

console = Console()


def profile(
    notebook: str = typer.Argument(..., help="Path to notebook"),
    var: str = typer.Option(..., "--var", "-v", help="Variable name to profile"),
    format: str = typer.Option("text", "--format", "-f", help="Output format: text, json"),
) -> None:
    """Profile a DataFrame variable in the notebook kernel."""
    adapter = JupyterAdapter(notebook)

    # Start kernel and replay executed cells
    kernel = DasaKernelManager()
    try:
        kernel.start()

        # Replay previously-executed cells to restore state
        for cell in adapter.code_cells:
            if cell.execution_count is not None:
                result = kernel.execute(cell.source, timeout=60)
                if not result.success:
                    console.print(
                        f"[yellow]Warning: Cell {cell.index} failed during replay: "
                        f"{result.error_type}: {result.error}[/yellow]"
                    )

        # Profile the variable
        profiler = Profiler(kernel)
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

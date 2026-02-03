"""Profile command implementation."""

import json
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from dasa.notebook.jupyter import JupyterAdapter
from dasa.notebook.kernel import KernelManager
from dasa.analysis.profiler import Profiler, DataFrameProfile
from dasa.output.formatter import format_bytes

console = Console()


def profile(
    notebook: str = typer.Argument(..., help="Path to notebook"),
    var: str = typer.Option(..., "--var", "-v", help="Variable name to profile"),
    sample: int = typer.Option(5, "--sample", "-s", help="Number of sample rows"),
    format_output: str = typer.Option("text", "--format", "-f", help="Output format: text, json"),
) -> None:
    """Profile a variable in the notebook kernel."""

    # Load notebook
    adapter = JupyterAdapter(notebook)

    # Start kernel and run cells to populate state
    kernel = KernelManager(adapter.kernel_spec or "python3")
    kernel.start()

    try:
        # Execute all code cells up to current state
        for cell in adapter.code_cells:
            if cell.execution_count:
                kernel.execute(cell.source)

        # Get variable type
        profiler = Profiler(kernel)
        var_type = profiler.get_variable_type(var)

        if var_type == "DataFrame":
            df_profile = profiler.profile_dataframe(var, sample)

            if format_output == "json":
                console.print(json.dumps(_profile_to_dict(df_profile), indent=2))
            else:
                _print_dataframe_profile(df_profile)
        else:
            console.print(f"Variable '{var}' is type {var_type} (only DataFrame profiling supported)")

    finally:
        kernel.shutdown()


def _profile_to_dict(profile: DataFrameProfile) -> dict:
    """Convert profile to dictionary."""
    return {
        "name": profile.name,
        "shape": list(profile.shape),
        "memory_bytes": profile.memory_bytes,
        "columns": [
            {
                "name": c.name,
                "dtype": c.dtype,
                "count": c.count,
                "unique_count": c.unique_count,
                "null_count": c.null_count,
                "null_percent": c.null_percent,
                "min_value": c.min_value,
                "max_value": c.max_value,
                "mean_value": c.mean_value,
                "std_value": c.std_value,
                "top_values": c.top_values,
                "issues": c.issues
            }
            for c in profile.columns
        ],
        "issues": profile.issues,
        "sample_rows": profile.sample_rows
    }


def _print_dataframe_profile(profile: DataFrameProfile) -> None:
    """Print DataFrame profile in human-readable format."""

    console.print(f"\n[bold]DataFrame: {profile.name}[/bold]")
    console.print(f"Shape: {profile.shape[0]:,} rows x {profile.shape[1]} columns")
    console.print(f"Memory: {format_bytes(profile.memory_bytes)}")
    console.print()

    # Columns table
    table = Table(show_header=True, header_style="bold")
    table.add_column("Column")
    table.add_column("Type")
    table.add_column("Non-Null")
    table.add_column("Unique")
    table.add_column("Stats / Values")
    table.add_column("Issues")

    for col in profile.columns:
        non_null = f"{col.count - col.null_count:,} ({100 - col.null_percent:.1f}%)"

        if col.mean_value is not None:
            stats = f"min={col.min_value:.1f}, max={col.max_value:.1f}, mean={col.mean_value:.1f}"
        elif col.top_values:
            top = [f"'{v[0]}'" for v in col.top_values[:3]]
            stats = f"{', '.join(top)}"
        elif col.min_value:
            stats = f"{col.min_value} to {col.max_value}"
        else:
            stats = "-"

        issues = ", ".join(col.issues) if col.issues else ""

        table.add_row(
            col.name,
            col.dtype,
            non_null,
            str(col.unique_count),
            stats,
            f"[yellow]{issues}[/yellow]" if issues else ""
        )

    console.print(table)

    # Issues summary
    if profile.issues:
        console.print("\n[bold yellow]Data Quality Issues:[/bold yellow]")
        for issue in profile.issues:
            console.print(f"  ! {issue}")

    # Sample rows
    if profile.sample_rows:
        console.print(f"\n[bold]Sample ({len(profile.sample_rows)} rows):[/bold]")
        sample_table = Table(show_header=True)
        for col in profile.columns[:6]:  # Limit columns
            sample_table.add_column(col.name)

        for row in profile.sample_rows:
            values = [str(row.get(col.name, ""))[:20] for col in profile.columns[:6]]
            sample_table.add_row(*values)

        console.print(sample_table)

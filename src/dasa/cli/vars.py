"""Vars command implementation."""

import json
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from dasa.notebook.jupyter import JupyterAdapter
from dasa.notebook.kernel import KernelManager
from dasa.analysis.deps import DependencyAnalyzer
from dasa.output.formatter import format_bytes

console = Console()


VARS_CODE = '''
import json
import sys

def _dasa_get_vars():
    """Get all user-defined variables."""
    results = []

    for name in dir():
        if name.startswith('_'):
            continue
        try:
            obj = eval(name)
            var_info = {
                "name": name,
                "type": type(obj).__name__,
                "size": sys.getsizeof(obj)
            }

            # Get more accurate size for DataFrames
            if hasattr(obj, 'memory_usage'):
                try:
                    var_info["size"] = int(obj.memory_usage(deep=True).sum())
                except:
                    pass

            # Get shape for arrays/dataframes
            if hasattr(obj, 'shape'):
                var_info["shape"] = list(obj.shape)

            results.append(var_info)
        except:
            pass

    return results

# Get from global namespace
_dasa_vars = []
for name in list(globals().keys()):
    if name.startswith('_'):
        continue
    if name in ['In', 'Out', 'get_ipython', 'exit', 'quit']:
        continue
    try:
        obj = globals()[name]
        if callable(obj) and not hasattr(obj, 'shape'):
            # Skip functions/classes unless they're arrays
            if type(obj).__name__ in ['function', 'type', 'module']:
                continue

        import sys
        var_info = {
            "name": name,
            "type": type(obj).__name__,
            "size": sys.getsizeof(obj)
        }

        if hasattr(obj, 'memory_usage'):
            try:
                var_info["size"] = int(obj.memory_usage(deep=True).sum())
            except:
                pass

        if hasattr(obj, 'shape'):
            var_info["shape"] = list(obj.shape)

        _dasa_vars.append(var_info)
    except:
        pass

print(json.dumps(_dasa_vars))
'''


def vars_cmd(
    notebook: str = typer.Argument(..., help="Path to notebook"),
    format_output: str = typer.Option("text", "--format", "-f", help="Output format: text, json"),
) -> None:
    """List variables in kernel memory with metadata."""

    adapter = JupyterAdapter(notebook)
    kernel = KernelManager(adapter.kernel_spec or "python3")

    # Build dependency graph to know where vars are used
    dep_analyzer = DependencyAnalyzer()
    graph = dep_analyzer.build_graph(adapter)

    # Track which cell defines each variable
    var_definitions: dict[str, int] = {}
    var_usages: dict[str, list[int]] = {}

    for cell_idx, node in graph.nodes.items():
        for defn in node.definitions:
            var_definitions[defn] = cell_idx
        for ref in node.references:
            if ref not in var_usages:
                var_usages[ref] = []
            var_usages[ref].append(cell_idx)

    try:
        kernel.start()

        # Execute all cells to populate state
        for cell in adapter.code_cells:
            if cell.execution_count is not None:
                kernel.execute(cell.source)

        # Get variables
        result = kernel.execute(VARS_CODE)

        if not result.success:
            console.print(f"[red]Error getting variables: {result.error}[/red]")
            raise typer.Exit(1)

        variables = json.loads(result.stdout.strip())

        if format_output == "json":
            # Enrich with definition/usage info
            for var in variables:
                var["defined_in"] = var_definitions.get(var["name"])
                var["used_in"] = var_usages.get(var["name"], [])
            console.print(json.dumps(variables, indent=2))
            return

        # Text output
        console.print("\n[bold]Variables in Kernel Memory[/bold]\n")

        if not variables:
            console.print("[dim]No user-defined variables found[/dim]")
            return

        table = Table(show_header=True, header_style="bold")
        table.add_column("Name")
        table.add_column("Type")
        table.add_column("Size")
        table.add_column("Shape")
        table.add_column("Defined")
        table.add_column("Used In")

        for var in sorted(variables, key=lambda x: x["size"], reverse=True):
            name = var["name"]
            shape = str(var.get("shape", "-")) if var.get("shape") else "-"
            defined = f"Cell {var_definitions.get(name, '?')}"
            used_in = var_usages.get(name, [])
            used_str = ", ".join(f"Cell {i}" for i in used_in[:3])
            if len(used_in) > 3:
                used_str += f" (+{len(used_in) - 3})"

            table.add_row(
                name,
                var["type"],
                format_bytes(var["size"]),
                shape,
                defined,
                used_str or "-"
            )

        console.print(table)

    finally:
        kernel.shutdown()

# Sprint 2: Understanding Tools

**Goal:** Implement the core understanding tools that make DASA valuable: `profile`, `validate`, `deps`.

**Duration:** ~3-4 days

**Prerequisite:** Sprint 1 (Core infrastructure)

**Eval Target:** Improve Data Understanding (DU), State Recovery (SR), and Dependency Reasoning (DR) task categories.

---

## Deliverables

| # | Deliverable | Description |
|---|-------------|-------------|
| 1 | `dasa profile` | Deep data profiling for variables |
| 2 | `dasa validate` | Notebook state consistency checking |
| 3 | `dasa deps` | Cell dependency analysis |

---

## Tasks

### 2.1 Profile Command

#### `src/dasa/analysis/profiler.py`

```python
"""Data profiling engine."""

import json
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ColumnProfile:
    """Profile of a single DataFrame column."""
    name: str
    dtype: str
    count: int
    unique_count: int
    null_count: int
    null_percent: float
    
    # Numeric columns
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    mean_value: Optional[float] = None
    std_value: Optional[float] = None
    
    # Categorical columns
    top_values: Optional[list[tuple[str, int]]] = None
    
    # Issues detected
    issues: list[str] = field(default_factory=list)


@dataclass
class DataFrameProfile:
    """Complete profile of a DataFrame."""
    name: str
    shape: tuple[int, int]
    memory_bytes: int
    columns: list[ColumnProfile]
    issues: list[str] = field(default_factory=list)
    sample_rows: Optional[list[dict]] = None


PROFILE_CODE = '''
import json
import pandas as pd
import numpy as np

def _dasa_profile(df, var_name, sample_n=5):
    """Generate DataFrame profile."""
    profile = {
        "name": var_name,
        "shape": list(df.shape),
        "memory_bytes": int(df.memory_usage(deep=True).sum()),
        "columns": [],
        "issues": [],
        "sample_rows": df.head(sample_n).to_dict("records")
    }
    
    for col in df.columns:
        col_data = df[col]
        col_profile = {
            "name": col,
            "dtype": str(col_data.dtype),
            "count": int(len(col_data)),
            "unique_count": int(col_data.nunique()),
            "null_count": int(col_data.isnull().sum()),
            "null_percent": float(col_data.isnull().sum() / len(col_data) * 100),
            "issues": []
        }
        
        # Numeric columns
        if pd.api.types.is_numeric_dtype(col_data):
            col_profile["min_value"] = float(col_data.min()) if not pd.isna(col_data.min()) else None
            col_profile["max_value"] = float(col_data.max()) if not pd.isna(col_data.max()) else None
            col_profile["mean_value"] = float(col_data.mean()) if not pd.isna(col_data.mean()) else None
            col_profile["std_value"] = float(col_data.std()) if not pd.isna(col_data.std()) else None
            
            # Check for issues
            if col_data.min() < 0 and col_data.max() > 0:
                neg_count = (col_data < 0).sum()
                if neg_count < len(col_data) * 0.1:  # Less than 10% negative
                    col_profile["issues"].append(f"{neg_count} negative values")
        
        # Categorical/object columns
        elif col_data.dtype == 'object' or str(col_data.dtype) == 'category':
            value_counts = col_data.value_counts().head(5)
            col_profile["top_values"] = [
                [str(k), int(v)] for k, v in value_counts.items()
            ]
        
        # Datetime columns
        elif pd.api.types.is_datetime64_any_dtype(col_data):
            col_profile["min_value"] = str(col_data.min())
            col_profile["max_value"] = str(col_data.max())
        
        # Check null percentage
        if col_profile["null_percent"] > 5:
            col_profile["issues"].append(f"{col_profile['null_percent']:.1f}% null")
            profile["issues"].append(f"{col}: {col_profile['null_percent']:.1f}% null")
        
        profile["columns"].append(col_profile)
    
    return profile

_dasa_result = _dasa_profile({var_name}, "{var_name}", {sample_n})
print(json.dumps(_dasa_result))
'''


class Profiler:
    """Data profiling engine."""
    
    def __init__(self, kernel):
        self.kernel = kernel
    
    def profile_dataframe(
        self,
        var_name: str,
        sample_n: int = 5
    ) -> DataFrameProfile:
        """Profile a DataFrame variable."""
        
        code = PROFILE_CODE.format(var_name=var_name, sample_n=sample_n)
        result = self.kernel.execute(code)
        
        if not result.success:
            raise RuntimeError(f"Failed to profile {var_name}: {result.error}")
        
        data = json.loads(result.stdout)
        
        columns = [
            ColumnProfile(
                name=c["name"],
                dtype=c["dtype"],
                count=c["count"],
                unique_count=c["unique_count"],
                null_count=c["null_count"],
                null_percent=c["null_percent"],
                min_value=c.get("min_value"),
                max_value=c.get("max_value"),
                mean_value=c.get("mean_value"),
                std_value=c.get("std_value"),
                top_values=c.get("top_values"),
                issues=c.get("issues", [])
            )
            for c in data["columns"]
        ]
        
        return DataFrameProfile(
            name=data["name"],
            shape=tuple(data["shape"]),
            memory_bytes=data["memory_bytes"],
            columns=columns,
            issues=data.get("issues", []),
            sample_rows=data.get("sample_rows")
        )
    
    def get_variable_type(self, var_name: str) -> str:
        """Get the type of a variable."""
        code = f"print(type({var_name}).__name__)"
        result = self.kernel.execute(code)
        
        if not result.success:
            raise NameError(f"Variable '{var_name}' not found")
        
        return result.stdout.strip()
```

#### `src/dasa/cli/profile.py`

```python
"""Profile command implementation."""

import typer
from rich.console import Console
from rich.table import Table

from dasa.notebook.jupyter import JupyterAdapter
from dasa.notebook.kernel import KernelManager
from dasa.analysis.profiler import Profiler
from dasa.output.formatter import format_bytes

console = Console()


def profile(
    notebook: str = typer.Argument(..., help="Path to notebook"),
    var: str = typer.Option(..., "--var", "-v", help="Variable name to profile"),
    sample: int = typer.Option(5, "--sample", "-s", help="Number of sample rows"),
    format: str = typer.Option("text", "--format", "-f", help="Output format: text, json"),
):
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
            profile = profiler.profile_dataframe(var, sample)
            
            if format == "json":
                import json
                console.print(json.dumps(profile.__dict__, default=str, indent=2))
            else:
                _print_dataframe_profile(profile)
        else:
            console.print(f"Variable '{var}' is type {var_type} (only DataFrame profiling supported)")
    
    finally:
        kernel.shutdown()


def _print_dataframe_profile(profile):
    """Print DataFrame profile in human-readable format."""
    
    console.print(f"\n[bold]DataFrame: {profile.name}[/bold]")
    console.print(f"Shape: {profile.shape[0]:,} rows × {profile.shape[1]} columns")
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
            console.print(f"  ⚠ {issue}")
    
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
```

---

### 2.2 Validate Command

#### `src/dasa/analysis/state.py`

```python
"""Notebook state analysis."""

from dataclasses import dataclass, field
from typing import Optional

from dasa.notebook.base import NotebookAdapter, Cell
from dasa.analysis.parser import parse_cell


@dataclass
class StateIssue:
    """A state consistency issue."""
    severity: str  # "error", "warning"
    cell_index: int
    message: str
    suggestion: Optional[str] = None


@dataclass
class StateAnalysis:
    """Complete state analysis result."""
    is_consistent: bool
    issues: list[StateIssue]
    execution_order: list[int]
    correct_order: list[int]
    defined_vars: dict[str, int]  # var -> cell that defines it
    undefined_refs: list[tuple[int, str]]  # (cell, var) pairs


class StateAnalyzer:
    """Analyzes notebook state for consistency issues."""
    
    def analyze(self, adapter: NotebookAdapter) -> StateAnalysis:
        """Analyze notebook state."""
        
        issues: list[StateIssue] = []
        defined_vars: dict[str, int] = {}
        undefined_refs: list[tuple[int, str]] = []
        
        # Track what's defined at each point
        current_definitions: set[str] = set()
        
        for cell in adapter.code_cells:
            analysis = parse_cell(cell.source)
            
            # Check for undefined references
            for ref in analysis.references:
                if ref not in current_definitions:
                    undefined_refs.append((cell.index, ref))
                    issues.append(StateIssue(
                        severity="error",
                        cell_index=cell.index,
                        message=f"Uses undefined variable '{ref}'",
                        suggestion=f"Make sure a cell defining '{ref}' runs before this cell"
                    ))
            
            # Track definitions
            for defn in analysis.definitions:
                if defn in defined_vars and defined_vars[defn] != cell.index:
                    # Redefinition - might be intentional
                    pass
                defined_vars[defn] = cell.index
                current_definitions.add(defn)
        
        # Check execution order
        execution_order = adapter.execution_order
        correct_order = list(range(len(adapter.code_cells)))
        
        # Detect out-of-order execution
        if execution_order:
            # Check if execution order matches cell order
            cell_indices = [c.index for c in adapter.code_cells]
            exec_positions = {idx: pos for pos, idx in enumerate(execution_order)}
            
            for i, cell_idx in enumerate(cell_indices[:-1]):
                next_idx = cell_indices[i + 1]
                if cell_idx in exec_positions and next_idx in exec_positions:
                    if exec_positions[cell_idx] > exec_positions[next_idx]:
                        issues.append(StateIssue(
                            severity="warning",
                            cell_index=next_idx,
                            message=f"Executed before Cell {cell_idx} (out of order)",
                            suggestion="Re-run cells in order"
                        ))
        
        # Check for cells with no execution count (never run)
        for cell in adapter.code_cells:
            if cell.execution_count is None:
                issues.append(StateIssue(
                    severity="warning",
                    cell_index=cell.index,
                    message="Cell has never been executed",
                    suggestion="Run this cell"
                ))
        
        # Determine if consistent
        has_errors = any(i.severity == "error" for i in issues)
        
        return StateAnalysis(
            is_consistent=not has_errors,
            issues=issues,
            execution_order=execution_order,
            correct_order=correct_order,
            defined_vars=defined_vars,
            undefined_refs=undefined_refs
        )
```

#### `src/dasa/cli/validate.py`

```python
"""Validate command implementation."""

import typer
from rich.console import Console

from dasa.notebook.jupyter import JupyterAdapter
from dasa.analysis.state import StateAnalyzer

console = Console()


def validate(
    notebook: str = typer.Argument(..., help="Path to notebook"),
    strict: bool = typer.Option(False, "--strict", help="Fail on any warning"),
    format: str = typer.Option("text", "--format", "-f", help="Output format: text, json"),
):
    """Check notebook state for consistency issues."""
    
    adapter = JupyterAdapter(notebook)
    analyzer = StateAnalyzer()
    analysis = analyzer.analyze(adapter)
    
    if format == "json":
        import json
        console.print(json.dumps({
            "is_consistent": analysis.is_consistent,
            "issues": [
                {
                    "severity": i.severity,
                    "cell_index": i.cell_index,
                    "message": i.message,
                    "suggestion": i.suggestion
                }
                for i in analysis.issues
            ],
            "execution_order": analysis.execution_order,
            "correct_order": analysis.correct_order
        }, indent=2))
        return
    
    # Text output
    console.print("\n[bold]Notebook State Analysis[/bold]\n")
    
    if analysis.is_consistent and not analysis.issues:
        console.print("[green]✓ Notebook state is consistent[/green]")
    elif analysis.is_consistent:
        console.print("[yellow]⚠ Notebook state has warnings[/yellow]")
    else:
        console.print("[red]✗ INCONSISTENT STATE DETECTED[/red]")
    
    # Show issues
    if analysis.issues:
        console.print("\n[bold]Issues:[/bold]")
        for issue in analysis.issues:
            icon = "✗" if issue.severity == "error" else "⚠"
            color = "red" if issue.severity == "error" else "yellow"
            console.print(f"  [{color}]{icon}[/{color}] Cell {issue.cell_index}: {issue.message}")
            if issue.suggestion:
                console.print(f"      → {issue.suggestion}")
    
    # Show execution order
    if analysis.execution_order:
        console.print(f"\n[bold]Execution Order:[/bold]")
        order_str = " → ".join(f"[{i}]" for i in analysis.execution_order)
        console.print(f"  Actual: {order_str}")
        
        correct_str = " → ".join(f"[{i}]" for i in analysis.correct_order)
        if analysis.execution_order != analysis.correct_order:
            console.print(f"  Correct: {correct_str}")
    
    # Exit code
    if strict and analysis.issues:
        raise typer.Exit(1)
    elif not analysis.is_consistent:
        raise typer.Exit(1)
```

---

### 2.3 Deps Command

#### `src/dasa/analysis/deps.py`

```python
"""Cell dependency analysis."""

from dataclasses import dataclass, field
from typing import Optional

from dasa.notebook.base import NotebookAdapter
from dasa.analysis.parser import parse_cell, CellAnalysis


@dataclass
class CellNode:
    """A cell in the dependency graph."""
    index: int
    preview: str
    definitions: set[str]
    references: set[str]
    upstream: set[int] = field(default_factory=set)  # Cells this depends on
    downstream: set[int] = field(default_factory=set)  # Cells that depend on this


@dataclass
class DependencyGraph:
    """Complete dependency graph for a notebook."""
    nodes: dict[int, CellNode]
    
    def get_upstream(self, cell_index: int) -> list[int]:
        """Get all cells this cell depends on (transitively)."""
        if cell_index not in self.nodes:
            return []
        
        visited = set()
        queue = list(self.nodes[cell_index].upstream)
        
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            queue.extend(self.nodes[current].upstream)
        
        return sorted(visited)
    
    def get_downstream(self, cell_index: int) -> list[int]:
        """Get all cells affected by changes to this cell (transitively)."""
        if cell_index not in self.nodes:
            return []
        
        visited = set()
        queue = list(self.nodes[cell_index].downstream)
        
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            queue.extend(self.nodes[current].downstream)
        
        return sorted(visited)


class DependencyAnalyzer:
    """Analyzes cell dependencies in a notebook."""
    
    def build_graph(self, adapter: NotebookAdapter) -> DependencyGraph:
        """Build dependency graph from notebook."""
        
        nodes: dict[int, CellNode] = {}
        var_definitions: dict[str, int] = {}  # var -> cell that last defined it
        
        # First pass: parse all cells
        for cell in adapter.code_cells:
            analysis = parse_cell(cell.source)
            
            nodes[cell.index] = CellNode(
                index=cell.index,
                preview=cell.preview,
                definitions=analysis.definitions,
                references=analysis.references
            )
        
        # Second pass: build edges
        for cell in adapter.code_cells:
            node = nodes[cell.index]
            
            # Find upstream dependencies (cells that define vars we reference)
            for ref in node.references:
                if ref in var_definitions:
                    defining_cell = var_definitions[ref]
                    node.upstream.add(defining_cell)
                    nodes[defining_cell].downstream.add(cell.index)
            
            # Update definitions
            for defn in node.definitions:
                var_definitions[defn] = cell.index
        
        return DependencyGraph(nodes=nodes)
```

#### `src/dasa/cli/deps.py`

```python
"""Deps command implementation."""

import typer
from rich.console import Console
from rich.tree import Tree

from dasa.notebook.jupyter import JupyterAdapter
from dasa.analysis.deps import DependencyAnalyzer

console = Console()


def deps(
    notebook: str = typer.Argument(..., help="Path to notebook"),
    cell: int = typer.Option(None, "--cell", "-c", help="Show impact of modifying this cell"),
    format: str = typer.Option("text", "--format", "-f", help="Output format: text, json, dot"),
):
    """Analyze cell dependencies in a notebook."""
    
    adapter = JupyterAdapter(notebook)
    analyzer = DependencyAnalyzer()
    graph = analyzer.build_graph(adapter)
    
    if format == "json":
        import json
        data = {
            "cells": [
                {
                    "index": node.index,
                    "preview": node.preview,
                    "definitions": list(node.definitions),
                    "references": list(node.references),
                    "upstream": list(node.upstream),
                    "downstream": list(node.downstream)
                }
                for node in graph.nodes.values()
            ]
        }
        if cell is not None:
            data["impact"] = {
                "cell": cell,
                "affected": graph.get_downstream(cell)
            }
        console.print(json.dumps(data, indent=2))
        return
    
    # Text output
    if cell is not None:
        # Show impact of modifying a specific cell
        _show_cell_impact(graph, cell)
    else:
        # Show full dependency graph
        _show_full_graph(graph)


def _show_full_graph(graph: DependencyGraph):
    """Show full dependency graph."""
    
    console.print("\n[bold]Dependency Graph[/bold]\n")
    
    for idx in sorted(graph.nodes.keys()):
        node = graph.nodes[idx]
        
        # Cell header
        defs = ", ".join(sorted(node.definitions)[:5])
        defs_str = f" - defines: {defs}" if defs else ""
        
        if not node.downstream:
            terminal = " [dim][TERMINAL][/dim]"
        else:
            terminal = ""
        
        console.print(f"[bold]Cell {idx}[/bold] ({node.preview}){defs_str}{terminal}")
        
        # Downstream
        if node.downstream:
            downstream = ", ".join(f"Cell {i}" for i in sorted(node.downstream))
            console.print(f"  └─→ {downstream}")
        
        console.print()


def _show_cell_impact(graph: DependencyGraph, cell_index: int):
    """Show impact of modifying a cell."""
    
    if cell_index not in graph.nodes:
        console.print(f"[red]Cell {cell_index} not found[/red]")
        raise typer.Exit(1)
    
    node = graph.nodes[cell_index]
    affected = graph.get_downstream(cell_index)
    
    console.print(f"\n[bold]If you modify Cell {cell_index}:[/bold]")
    console.print(f"  Preview: {node.preview}")
    console.print(f"  Defines: {', '.join(sorted(node.definitions))}")
    console.print()
    
    if affected:
        console.print("[bold]Cells that need re-run:[/bold]")
        for idx in affected:
            affected_node = graph.nodes[idx]
            # Find which variables connect them
            shared = node.definitions & affected_node.references
            via = f" (uses: {', '.join(shared)})" if shared else ""
            console.print(f"  → Cell {idx}{via}")
        
        console.print(f"\n[bold]Total:[/bold] {len(affected)} cells affected")
    else:
        console.print("[green]No downstream dependencies - safe to modify[/green]")
```

---

### 2.4 Register Commands

Update `src/dasa/cli/main.py`:

```python
"""DASA CLI entry point."""

import typer
from rich.console import Console

from dasa.cli.profile import profile
from dasa.cli.validate import validate
from dasa.cli.deps import deps

app = typer.Typer(
    name="dasa",
    help="Data Science Agent toolkit for notebooks",
    no_args_is_help=True
)

console = Console()

# Register commands
app.command()(profile)
app.command()(validate)
app.command()(deps)


@app.command()
def version():
    """Show DASA version."""
    from dasa import __version__
    console.print(f"dasa {__version__}")


if __name__ == "__main__":
    app()
```

---

## Acceptance Criteria

- [ ] `dasa profile notebook.ipynb --var df` shows DataFrame structure
- [ ] `dasa validate notebook.ipynb` detects state issues
- [ ] `dasa deps notebook.ipynb` shows dependency graph
- [ ] `dasa deps notebook.ipynb --cell 1` shows impact analysis
- [ ] All commands support `--format json`
- [ ] Unit tests pass
- [ ] Eval shows improvement on DU, SR, DR tasks

---

## Eval Checkpoints

After Sprint 2, run evaluation and compare to baseline:

| Category | Baseline | Target | 
|----------|----------|--------|
| Data Understanding (DU) | ~50% | >70% |
| State Recovery (SR) | ~30% | >50% |
| Dependency Reasoning (DR) | ~40% | >65% |

```bash
cd eval
python -m harness.runner --condition with_dasa --output results/sprint2.json
python -m harness.analyze results/baseline.json results/sprint2.json
```

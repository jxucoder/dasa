# Sprint 3: Execution Tools

**Goal:** Implement `run` and `replay` commands for cell execution and reproducibility verification.

**Duration:** ~2-3 days

**Prerequisite:** Sprint 2 (Understanding tools)

**Eval Target:** Improve Bug Fixing (BF) and Reproducibility (RP) task categories.

---

## Deliverables

| # | Deliverable | Description |
|---|-------------|-------------|
| 1 | `dasa run` | Execute cells with rich error context |
| 2 | `dasa replay` | Run notebook from scratch, verify reproducibility |

---

## Tasks

### 3.1 Run Command

#### `src/dasa/cli/run.py`

```python
"""Run command implementation."""

import time
import difflib
import typer
from rich.console import Console

from dasa.notebook.jupyter import JupyterAdapter
from dasa.notebook.kernel import KernelManager, ExecutionResult
from dasa.analysis.profiler import Profiler
from dasa.output.formatter import format_error, format_execution_result

console = Console()


def run(
    notebook: str = typer.Argument(..., help="Path to notebook"),
    cell: int = typer.Option(None, "--cell", "-c", help="Run specific cell"),
    from_cell: int = typer.Option(None, "--from", help="Run from cell N to end"),
    to_cell: int = typer.Option(None, "--to", help="Run from start to cell N"),
    all_cells: bool = typer.Option(False, "--all", help="Run all cells"),
    stale: bool = typer.Option(False, "--stale", help="Run stale cells only"),
    timeout: int = typer.Option(300, "--timeout", "-t", help="Timeout in seconds"),
    format: str = typer.Option("text", "--format", "-f", help="Output format"),
):
    """Execute notebook cells."""
    
    adapter = JupyterAdapter(notebook)
    kernel = KernelManager(adapter.kernel_spec or "python3")
    
    try:
        kernel.start()
        
        # Determine which cells to run
        cells_to_run = _get_cells_to_run(
            adapter, cell, from_cell, to_cell, all_cells, stale
        )
        
        if not cells_to_run:
            console.print("[yellow]No cells to run[/yellow]")
            return
        
        results = []
        
        for cell_obj in cells_to_run:
            console.print(f"Running Cell {cell_obj.index}...", end=" ")
            
            start = time.time()
            result = kernel.execute(cell_obj.source, timeout=timeout)
            elapsed = time.time() - start
            
            if result.success:
                console.print(f"[green]✓[/green] ({elapsed:.2f}s)")
            else:
                console.print(f"[red]✗[/red] ({elapsed:.2f}s)")
            
            # Show detailed result
            _show_execution_result(
                cell_obj.index,
                result,
                elapsed,
                cell_obj.source,
                kernel,
                format
            )
            
            results.append({
                "cell": cell_obj.index,
                "success": result.success,
                "elapsed": elapsed
            })
        
        # Summary
        success_count = sum(1 for r in results if r["success"])
        console.print(f"\n[bold]Summary:[/bold] {success_count}/{len(results)} cells succeeded")
        
    finally:
        kernel.shutdown()


def _get_cells_to_run(adapter, cell, from_cell, to_cell, all_cells, stale):
    """Determine which cells to run based on options."""
    
    code_cells = adapter.code_cells
    
    if cell is not None:
        # Run single cell
        return [c for c in code_cells if c.index == cell]
    
    if all_cells:
        return code_cells
    
    if from_cell is not None:
        return [c for c in code_cells if c.index >= from_cell]
    
    if to_cell is not None:
        return [c for c in code_cells if c.index <= to_cell]
    
    if stale:
        # TODO: Implement stale detection
        # For now, return cells with no execution count
        return [c for c in code_cells if c.execution_count is None]
    
    # Default: no cells (require explicit selection)
    return []


def _show_execution_result(
    cell_index: int,
    result: ExecutionResult,
    elapsed: float,
    source: str,
    kernel: KernelManager,
    format: str
):
    """Show detailed execution result."""
    
    if format == "json":
        import json
        console.print(json.dumps({
            "cell": cell_index,
            "success": result.success,
            "elapsed_seconds": elapsed,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "error": result.error,
            "error_type": result.error_type
        }, indent=2))
        return
    
    # Show stdout
    if result.stdout:
        console.print("\n[dim]Output:[/dim]")
        for line in result.stdout.strip().split('\n')[:15]:
            console.print(f"  {line}")
        if result.stdout.count('\n') > 15:
            console.print("  [dim]... (truncated)[/dim]")
    
    # Show error with context
    if not result.success:
        console.print(f"\n[red]Error: {result.error_type}: {result.error}[/red]")
        
        # Try to provide helpful context
        context = _build_error_context(
            result.error_type,
            result.error,
            source,
            result.traceback,
            kernel
        )
        
        if context.get("line"):
            console.print(f"\nLine {context['line_number']}: {context['line']}")
        
        if context.get("available"):
            console.print(f"\n[dim]Available: {', '.join(context['available'][:10])}[/dim]")
        
        if context.get("suggestion"):
            console.print(f"\n[yellow]Suggestion: {context['suggestion']}[/yellow]")


def _build_error_context(
    error_type: str,
    error_msg: str,
    source: str,
    traceback: list,
    kernel: KernelManager
) -> dict:
    """Build helpful context for an error."""
    
    context = {}
    
    # Try to find the line number from traceback
    if traceback:
        for line in traceback:
            if "--->" in line or "-->" in line:
                # Extract line number
                import re
                match = re.search(r'(\d+)', line)
                if match:
                    line_num = int(match.group(1))
                    lines = source.split('\n')
                    if 0 < line_num <= len(lines):
                        context["line_number"] = line_num
                        context["line"] = lines[line_num - 1].strip()
    
    # Error-specific context
    if error_type == "KeyError":
        # For DataFrame column errors, show available columns
        var_match = _extract_variable_from_error(error_msg, source)
        if var_match:
            try:
                cols_code = f"list({var_match}.columns)"
                result = kernel.execute(cols_code)
                if result.success:
                    import ast
                    context["available"] = ast.literal_eval(result.stdout.strip())
                    
                    # Find similar column name
                    missing_col = error_msg.strip("'\"")
                    similar = difflib.get_close_matches(
                        missing_col, context["available"], n=1, cutoff=0.6
                    )
                    if similar:
                        context["suggestion"] = f"Did you mean '{similar[0]}'?"
            except:
                pass
    
    elif error_type == "NameError":
        # Show what is defined
        missing_name = error_msg.split("'")[1] if "'" in error_msg else error_msg
        
        # Get defined names
        try:
            result = kernel.execute("dir()")
            if result.success:
                import ast
                defined = ast.literal_eval(result.stdout.strip())
                user_vars = [v for v in defined if not v.startswith('_')]
                
                similar = difflib.get_close_matches(
                    missing_name, user_vars, n=1, cutoff=0.6
                )
                if similar:
                    context["suggestion"] = f"Did you mean '{similar[0]}'?"
                    context["available"] = user_vars[:10]
        except:
            pass
    
    return context


def _extract_variable_from_error(error_msg: str, source: str) -> str:
    """Try to extract the DataFrame variable from error context."""
    import re
    
    # Look for patterns like df['col'] in source
    patterns = [
        r"(\w+)\s*\[",  # var[
        r"(\w+)\.loc",   # var.loc
        r"(\w+)\.iloc",  # var.iloc
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, source)
        if matches:
            return matches[0]
    
    return None
```

---

### 3.2 Replay Command

#### `src/dasa/cli/replay.py`

```python
"""Replay command implementation."""

import time
import hashlib
import typer
from rich.console import Console
from rich.table import Table

from dasa.notebook.jupyter import JupyterAdapter
from dasa.notebook.kernel import KernelManager

console = Console()


def replay(
    notebook: str = typer.Argument(..., help="Path to notebook"),
    compare: bool = typer.Option(True, "--compare/--no-compare", help="Compare outputs"),
    save: str = typer.Option(None, "--save", "-s", help="Save replayed notebook to file"),
    strict: bool = typer.Option(False, "--strict", help="Fail on any difference"),
    timeout: int = typer.Option(300, "--timeout", "-t", help="Timeout per cell"),
    format: str = typer.Option("text", "--format", "-f", help="Output format"),
):
    """Run notebook from scratch and verify reproducibility."""
    
    adapter = JupyterAdapter(notebook)
    kernel = KernelManager(adapter.kernel_spec or "python3")
    
    console.print(f"\n[bold]Replaying notebook from scratch (new kernel)...[/bold]\n")
    
    results = []
    issues = []
    
    try:
        kernel.start()
        
        for cell in adapter.code_cells:
            console.print(f"Cell {cell.index}: ", end="")
            
            start = time.time()
            result = kernel.execute(cell.source, timeout=timeout)
            elapsed = time.time() - start
            
            cell_result = {
                "cell": cell.index,
                "preview": cell.preview,
                "success": result.success,
                "elapsed": elapsed,
                "output_match": None,
                "issue": None
            }
            
            if result.success:
                # Compare outputs if enabled
                if compare and cell.outputs:
                    original_hash = _hash_outputs(cell.outputs)
                    new_hash = _hash_output(result.stdout, result.result)
                    
                    if original_hash == new_hash:
                        console.print(f"[green]✓[/green] ({elapsed:.2f}s) - outputs match")
                        cell_result["output_match"] = True
                    else:
                        console.print(f"[yellow]⚠[/yellow] ({elapsed:.2f}s) - OUTPUT DIFFERS")
                        cell_result["output_match"] = False
                        cell_result["issue"] = "Output differs from original"
                        issues.append({
                            "cell": cell.index,
                            "type": "output_differs",
                            "message": "Output differs from original run"
                        })
                else:
                    console.print(f"[green]✓[/green] ({elapsed:.2f}s)")
                    cell_result["output_match"] = True
            else:
                console.print(f"[red]✗ FAILED[/red] ({elapsed:.2f}s)")
                console.print(f"    Error: {result.error_type}: {result.error}")
                
                cell_result["issue"] = f"{result.error_type}: {result.error}"
                issues.append({
                    "cell": cell.index,
                    "type": "execution_error",
                    "error_type": result.error_type,
                    "message": result.error
                })
            
            results.append(cell_result)
        
    finally:
        kernel.shutdown()
    
    # Summary
    _show_summary(results, issues, format)
    
    # Suggest fixes for issues
    if issues:
        _suggest_fixes(issues)
    
    # Exit code
    if strict and issues:
        raise typer.Exit(1)
    elif any(not r["success"] for r in results):
        raise typer.Exit(1)


def _hash_outputs(outputs: list) -> str:
    """Hash cell outputs for comparison."""
    content = ""
    for output in outputs:
        if output.get("output_type") == "stream":
            content += output.get("text", "")
        elif output.get("output_type") == "execute_result":
            content += str(output.get("data", {}))
    return hashlib.md5(content.encode()).hexdigest()


def _hash_output(stdout: str, result: any) -> str:
    """Hash execution output for comparison."""
    content = stdout + str(result or "")
    return hashlib.md5(content.encode()).hexdigest()


def _show_summary(results: list, issues: list, format: str):
    """Show replay summary."""
    
    total = len(results)
    succeeded = sum(1 for r in results if r["success"])
    matched = sum(1 for r in results if r["output_match"])
    
    console.print(f"\n[bold]{'─' * 50}[/bold]")
    console.print(f"[bold]Total time:[/bold] {sum(r['elapsed'] for r in results):.1f}s")
    console.print(f"[bold]Cells executed:[/bold] {succeeded}/{total}")
    
    if total > 0:
        repro_score = matched / total * 100
        color = "green" if repro_score == 100 else "yellow" if repro_score > 80 else "red"
        console.print(f"[bold]Reproducibility Score:[/bold] [{color}]{repro_score:.0f}%[/{color}] ({matched}/{total} cells)")


def _suggest_fixes(issues: list):
    """Suggest fixes for reproducibility issues."""
    
    console.print(f"\n[bold yellow]Issues Found:[/bold yellow]")
    
    for i, issue in enumerate(issues, 1):
        console.print(f"\n  {i}. Cell {issue['cell']}: {issue['message']}")
        
        # Suggest fixes based on issue type
        if issue["type"] == "execution_error":
            if issue.get("error_type") == "FileNotFoundError":
                console.print("     [dim]→ Check if file exists and is committed to repo[/dim]")
            elif issue.get("error_type") == "ModuleNotFoundError":
                console.print("     [dim]→ Add missing package to requirements.txt[/dim]")
            elif issue.get("error_type") == "KeyError":
                console.print("     [dim]→ Check environment variables are set[/dim]")
        
        elif issue["type"] == "output_differs":
            console.print("     [dim]→ Set random seed with np.random.seed(42)[/dim]")
            console.print("     [dim]→ Check for non-deterministic operations[/dim]")
```

---

### 3.3 Update CLI Main

Update `src/dasa/cli/main.py` to register new commands:

```python
"""DASA CLI entry point."""

import typer
from rich.console import Console

from dasa.cli.profile import profile
from dasa.cli.validate import validate
from dasa.cli.deps import deps
from dasa.cli.run import run
from dasa.cli.replay import replay

app = typer.Typer(
    name="dasa",
    help="Data Science Agent toolkit for notebooks",
    no_args_is_help=True
)

console = Console()

# Understanding tools
app.command()(profile)
app.command()(validate)
app.command()(deps)

# Execution tools
app.command()(run)
app.command()(replay)


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

- [ ] `dasa run notebook.ipynb --cell 3` executes single cell
- [ ] `dasa run notebook.ipynb --all` executes all cells
- [ ] Error output includes helpful context (available columns, suggestions)
- [ ] `dasa replay notebook.ipynb` runs from scratch
- [ ] Replay shows reproducibility score
- [ ] Replay suggests fixes for common issues
- [ ] All commands support `--format json`
- [ ] Unit tests pass

---

## Eval Checkpoints

After Sprint 3 (MVP complete), run full evaluation:

| Category | Baseline | After Sprint 2 | After Sprint 3 (Target) |
|----------|----------|----------------|------------------------|
| Data Understanding (DU) | ~50% | ~70% | >75% |
| Bug Fixing (BF) | ~60% | ~60% | >80% |
| Visualization (VZ) | ~40% | ~55% | >65% |
| State Recovery (SR) | ~30% | ~50% | >60% |
| Dependency Reasoning (DR) | ~40% | ~65% | >70% |
| Reproducibility (RP) | ~35% | ~35% | >70% |
| **Overall** | **~43%** | **~56%** | **>70%** |

```bash
cd eval
python -m harness.runner --condition with_dasa --output results/sprint3.json
python -m harness.analyze results/baseline.json results/sprint3.json
```

**MVP Success Criteria:** Overall completion rate >70% with at least +25% improvement over baseline.

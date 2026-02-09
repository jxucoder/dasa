# Sprint 3: Hands + Memory — Run + Context

**Goal:** Implement cell execution with rich error context, and project memory for cross-conversation persistence.

**Duration:** ~3-4 days

**Prerequisite:** Sprint 2 (Eyes: profile + check)

**Eval Target:** Improve Bug Fixing (BF) and Reproducibility (RP) tasks. Context improves all categories.

---

## Deliverables

| # | Deliverable | Description |
|---|-------------|-------------|
| 1 | `dasa run` | Execute cells with rich error context, suggestions, dependency warnings |
| 2 | `dasa context` | Read/write persistent project memory across conversations |

---

## Tasks

### 3.1 Run Command

`dasa run notebook.ipynb --cell 5`

Execute cells with rich error context. When execution fails, provide the error, the line that caused it, available columns/variables, and a "did you mean?" suggestion.

**Flow:**
1. Load notebook, start kernel
2. Replay previously-executed cells to restore state
3. Execute target cell(s)
4. On success: show output, warn about stale downstream cells
5. On failure: build rich error context (available names, fuzzy match, suggestions)
6. **Auto-log** result to `.dasa/log`
7. **Auto-update** `.dasa/state.json` with new code hash

**Key features:**

- `--cell N` — run single cell
- `--from N` — run from cell N to end
- `--to N` — run from start to cell N
- `--all` — run all cells
- `--stale` — run only stale cells (detected via `.dasa/state.json`)
- `--timeout N` — timeout per cell (default 300s)

**Error context building:**

```python
def _build_error_context(error_type, error_msg, source, traceback, kernel):
    """Build helpful context for an error."""
    
    context = {}
    
    # Extract line number from traceback
    # ...
    
    if error_type == "KeyError":
        # Get available DataFrame columns
        # Fuzzy match against missing column name
        # Suggest closest match
        
    elif error_type == "NameError":
        # Get defined variables in kernel
        # Fuzzy match against missing name
        # Suggest closest match or "did you forget to run cell N?"
    
    return context
```

**Output examples:**

Success:
```
Running Cell 5... ✓ (0.3s)

Output:
  X shape: (47500, 3), y shape: (47500,)

⚠ Downstream cells may be stale: Cell 8, Cell 12
  Run `dasa run notebook.ipynb --from 8` to update
```

Failure:
```
Running Cell 8... ✗ (0.1s)

Error: KeyError: 'revenue_usd'
  Line 3: df['profit'] = df['revenue_usd'] - df['cost']

Available columns: user_id, age, score, region, revenue, cost
Suggestion: Did you mean 'revenue'?
```

See `src/dasa/cli/run.py` for the full implementation.

---

### 3.2 Context Command

`dasa context`

Read and write persistent project memory. This is what enables agents to pick up where the last conversation left off.

**Flow:**
1. Read `.dasa/context.yaml` and `.dasa/log`
2. Read cached profiles from `.dasa/profiles/`
3. Display formatted summary
4. Or: update specific fields via flags

**Subcommands / Options:**

```bash
# Read full context
dasa context

# Set project goal
dasa context --set-goal "Predict user churn, AUC > 0.80"

# Set status
dasa context --set-status "feature engineering"

# Log a decision
dasa context --log "Tried random forest, overfit. Switching to logistic regression."

# Show only recent log
dasa context --log-only --last 10

# JSON output (for programmatic use)
dasa context --format json
```

#### `src/dasa/cli/context.py`

```python
"""Context command — project memory management."""

import typer
from rich.console import Console
from rich.table import Table

from dasa.session.context import ContextManager
from dasa.session.log import SessionLog
from dasa.session.profiles import ProfileCache

console = Console()


def context(
    set_goal: str = typer.Option(None, "--set-goal", help="Set project goal"),
    set_status: str = typer.Option(None, "--set-status", help="Set project status"),
    set_name: str = typer.Option(None, "--set-name", help="Set project name"),
    log_message: str = typer.Option(None, "--log", help="Append to decision log"),
    log_only: bool = typer.Option(False, "--log-only", help="Show only recent log"),
    last: int = typer.Option(20, "--last", help="Number of recent log entries"),
    format: str = typer.Option("text", "--format", "-f", help="Output format: text, json"),
):
    """Read or update project context and memory."""
    
    ctx_mgr = ContextManager()
    session_log = SessionLog()
    profile_cache = ProfileCache()
    
    # Handle writes
    if any([set_goal, set_status, set_name]):
        ctx_mgr.ensure_session()
        ctx_mgr.update(goal=set_goal, status=set_status, name=set_name)
        
        if set_goal:
            session_log.append("user", f"Goal: {set_goal}")
            console.print(f"[green]Goal set:[/green] {set_goal}")
        if set_status:
            session_log.append("user", f"Status: {set_status}")
            console.print(f"[green]Status set:[/green] {set_status}")
        if set_name:
            console.print(f"[green]Name set:[/green] {set_name}")
        return
    
    if log_message:
        ctx_mgr.ensure_session()
        session_log.append("agent", log_message)
        console.print(f"[green]Logged:[/green] {log_message}")
        return
    
    # Handle reads
    ctx = ctx_mgr.read()
    
    if log_only:
        entries = session_log.read(last_n=last)
        for entry in entries:
            console.print(f"  {entry}")
        return
    
    if format == "json":
        _output_json(ctx, session_log, profile_cache)
        return
    
    # Full context display
    _print_context(ctx, session_log, profile_cache)


def _print_context(ctx, session_log, profile_cache):
    """Print full project context."""
    
    if not ctx.name and not ctx.goal:
        console.print("[dim]No project context yet. Set one with:[/dim]")
        console.print("  dasa context --set-goal 'Your goal here'")
        return
    
    # Project info
    if ctx.name:
        console.print(f"\n[bold]Project:[/bold] {ctx.name}")
    if ctx.goal:
        console.print(f"[bold]Goal:[/bold] {ctx.goal}")
    if ctx.status:
        console.print(f"[bold]Status:[/bold] {ctx.status}")
    if ctx.notebook:
        console.print(f"[bold]Notebook:[/bold] {ctx.notebook}")
    
    # Constraints
    if ctx.constraints:
        console.print(f"\n[bold]Constraints:[/bold]")
        for c in ctx.constraints:
            console.print(f"  - {c}")
    
    # Data profiles
    profiles = profile_cache.list_profiles()
    if profiles:
        console.print(f"\n[bold]Data:[/bold]")
        for name in profiles:
            profile = profile_cache.load(name)
            if profile:
                shape = profile.get("shape", [])
                source = profile.get("source", "")
                shape_str = f"{shape[0]:,} rows x {shape[1]} cols" if len(shape) == 2 else ""
                console.print(f"  {name}: {shape_str} ({source})")
    
    # Approaches
    if ctx.approaches:
        console.print(f"\n[bold]Tried:[/bold]")
        for approach in ctx.approaches:
            status_icon = "✓" if approach.get("status") == "current" else "✗"
            name = approach.get("name", "unknown")
            result = approach.get("result", "")
            reason = approach.get("reason", "")
            console.print(f"  {status_icon} {name} — {result}")
            if reason:
                console.print(f"    {reason}")
    
    # Recent log
    entries = session_log.read(last_n=10)
    if entries:
        console.print(f"\n[bold]Recent:[/bold]")
        for entry in entries:
            console.print(f"  {entry}")
```

---

### 3.3 Register Commands

Update `src/dasa/cli/main.py`:

```python
from dasa.cli.profile import profile
from dasa.cli.check import check
from dasa.cli.run import run
from dasa.cli.context import context

# Eyes
app.command()(profile)
app.command()(check)

# Hands + Memory
app.command()(run)
app.command()(context)
```

---

## Acceptance Criteria

- [ ] `dasa run notebook.ipynb --cell 3` executes single cell
- [ ] `dasa run notebook.ipynb --all` executes all cells
- [ ] `dasa run notebook.ipynb --stale` runs only stale cells
- [ ] Error output includes available columns/variables and "did you mean?" suggestions
- [ ] Run auto-logs to `.dasa/log` and updates `.dasa/state.json`
- [ ] `dasa context` shows project state, data profiles, approaches, recent log
- [ ] `dasa context --set-goal "..."` updates context
- [ ] `dasa context --log "..."` appends to log
- [ ] All commands support `--format json`
- [ ] Unit tests pass

---

## Eval Checkpoint — MVP Complete

After Sprint 3, run full evaluation:

| Category | Baseline | After Sprint 2 | After Sprint 3 (Target) |
|----------|----------|----------------|------------------------|
| Data Understanding (DU) | ~50% | ~70% | >75% |
| Bug Fixing (BF) | ~60% | ~60% | >80% |
| Visualization (VZ) | ~40% | ~55% | >65% |
| State Recovery (SR) | ~30% | ~50% | >60% |
| Dependency Reasoning (DR) | ~40% | ~65% | >70% |
| Reproducibility (RP) | ~35% | ~35% | >60% |
| **Overall** | **~43%** | **~56%** | **>70%** |

**MVP Success Criteria:** Overall completion rate >70% with at least +25% improvement over baseline.

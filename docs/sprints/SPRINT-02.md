# Sprint 2: Eyes — Profile + Check

**Goal:** Implement the two understanding commands that let agents see data and notebook state.

**Duration:** ~3-4 days

**Prerequisite:** Sprint 1 (Core + Session)

**Eval Target:** Improve Data Understanding (DU), State Recovery (SR), and Dependency Reasoning (DR) categories.

---

## Deliverables

| # | Deliverable | Description |
|---|-------------|-------------|
| 1 | `dasa profile` | Deep data profiling with auto-cache to `.dasa/profiles/` |
| 2 | `dasa check` | Notebook health: state validation + dependency graph + staleness |

---

## Tasks

### 2.1 Profile Command

`dasa profile notebook.ipynb --var df`

Profiles a variable in the kernel by injecting profiling code and parsing the result.

**Flow:**
1. Load notebook via JupyterAdapter
2. Start kernel, execute cells that have been previously run (replay state)
3. Inject profiling code for the target variable
4. Parse JSON result into `DataFrameProfile`
5. Display formatted output (rich table or JSON)
6. **Auto-cache** result to `.dasa/profiles/{var}.yaml`
7. **Auto-log** to `.dasa/log`: "Profiled {var}. {shape}. Issues: {issues}"

**Key components:**

- `src/dasa/analysis/profiler.py` — `Profiler` class, `PROFILE_CODE` template injected into kernel
- `src/dasa/cli/profile.py` — CLI command with `--var`, `--sample`, `--format` options

**Output example:**
```
DataFrame: df (50,000 rows × 12 columns)
Memory: 4.6 MB

Column      Type       Non-Null     Unique   Stats / Values              Issues
─────────────────────────────────────────────────────────────────────────────
user_id     int64      50,000 (100%) 50,000  min=1, max=50000
age         int64      47,659 (95%)  78      min=18, max=95, mean=42     4.7% null
revenue     float64    48,750 (98%)  12,341  min=-500, max=99847         2.5% null, 23 negative
region      object     50,000 (100%) 4       'North', 'South', 'East'
churned     int64      50,000 (100%) 2       values: [0, 1], mean=0.23

Data Quality Issues:
  ⚠ age: 4.7% null values
  ⚠ revenue: 2.5% null, has negative values
```

See `legacy_docs/sprints/SPRINT-02.md` for full profiler implementation.

---

### 2.2 Check Command

`dasa check notebook.ipynb`

One command that gives the agent a complete notebook health report. Combines three analyses:

1. **State validation** — undefined variables, never-executed cells, out-of-order execution
2. **Dependency graph** — which cells depend on which, what breaks if you change something
3. **Staleness detection** — which cells have been modified since last execution

**Flow:**
1. Load notebook via JupyterAdapter
2. Parse all code cells via AST parser
3. Run state analysis (undefined refs, execution order)
4. Build dependency graph (upstream/downstream for each cell)
5. Check staleness against `.dasa/state.json`
6. Display combined report
7. **Auto-log** findings to `.dasa/log`

**Key components:**

- `src/dasa/analysis/state.py` — `StateAnalyzer` class (from old `validate`)
- `src/dasa/analysis/deps.py` — `DependencyAnalyzer` class (from old `deps`)
- `src/dasa/cli/check.py` — Combined CLI command

**Output example:**
```
Notebook: analysis.ipynb (24 cells)

State:
  ✗ Cell 3: output is STALE (code modified after last run)
  ✗ Cell 8: uses undefined variable 'X'
  ⚠ Cell 10: never executed
  ✓ 21 cells consistent

Dependencies:
  Cell 0 (imports) → Cell 1, 2, 3, 4, 5
  Cell 1 (df = pd.read_csv...) → Cell 2, 3, 5, 8
  Cell 5 (features = ...) → Cell 8, 12

  If you modify Cell 1: 6 cells need re-run → [2, 3, 5, 8, 12]

Pipeline: [0] → [1] → [2] → [3] → [5] → [8] → [12]
Dead code: Cells 4, 6, 7, 9, 10, 11 (no downstream dependents)

Execution Order:
  Actual:  [0] → [1] → [3] → [2] → [5]  (out of order!)
  Correct: [0] → [1] → [2] → [3] → [5]
```

#### `src/dasa/cli/check.py`

```python
"""Check command — combined notebook health report."""

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
):
    """Check notebook health: state, dependencies, staleness."""
    
    adapter = JupyterAdapter(notebook)
    
    # Run all analyses
    state_analyzer = StateAnalyzer()
    state_analysis = state_analyzer.analyze(adapter)
    
    dep_analyzer = DependencyAnalyzer()
    dep_graph = dep_analyzer.build_graph(adapter)
    
    if format == "json":
        _output_json(state_analysis, dep_graph, cell)
        return
    
    # Combined text report
    _print_state_section(state_analysis)
    _print_deps_section(dep_graph, cell)
    _print_execution_order(state_analysis)
    
    # Auto-log findings
    log = SessionLog()
    issue_count = len(state_analysis.issues)
    if issue_count:
        log.append("check", f"Found {issue_count} issues in {notebook}")
    else:
        log.append("check", f"{notebook} is consistent")
    
    # Exit code
    if not state_analysis.is_consistent:
        raise typer.Exit(1)
```

---

### 2.3 Register Commands

Update `src/dasa/cli/main.py`:

```python
from dasa.cli.profile import profile
from dasa.cli.check import check

app.command()(profile)
app.command()(check)
```

---

## Acceptance Criteria

- [ ] `dasa profile notebook.ipynb --var df` shows DataFrame structure
- [ ] Profile auto-cached to `.dasa/profiles/df.yaml`
- [ ] `dasa check notebook.ipynb` shows state + deps + staleness in one report
- [ ] `dasa check notebook.ipynb --cell 1` shows impact of modifying cell 1
- [ ] All commands support `--format json`
- [ ] Both commands auto-log to `.dasa/log`
- [ ] Unit tests pass
- [ ] Eval shows improvement on DU, SR, DR tasks

---

## Eval Checkpoint

After Sprint 2, run evaluation and compare to baseline:

| Category | Baseline | Target |
|----------|----------|--------|
| Data Understanding (DU) | ~50% | >70% |
| State Recovery (SR) | ~30% | >50% |
| Dependency Reasoning (DR) | ~40% | >65% |

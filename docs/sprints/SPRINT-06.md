# Sprint 6: Reliability & Cross-Command Integration

**Goal:** Fix the critical state synchronization gap between commands, harden error handling, and make all four commands work together seamlessly.

**Duration:** ~3-4 days

**Prerequisite:** Sprint 5 (Extensions)

**Motivation:** Testing DASA end-to-end in the `example/` workspace revealed that the four commands don't share execution state. `dasa run` tracks execution in `state.json`, but `check` and `profile` only look at the notebook's `execution_count` field — which `run` never writes. This means `check` reports cells as "never executed" right after running them, and `profile` can't restore kernel state for cells executed via `dasa run`.

---

## Problems Found

### Critical: Two sources of truth for execution state

There are two separate sources of truth for "has this cell been executed?":

1. **`state.json`** (written by `dasa run`) — tracks code hashes and last-run timestamps
2. **Notebook `execution_count`** (in the `.ipynb` file) — the standard Jupyter field

These are never synchronized, breaking cross-command integration:

| Symptom | Root Cause | Impact |
|---------|-----------|--------|
| `dasa check` reports "never executed" for cells just run by `dasa run` | `StateAnalyzer.analyze()` only checks `cell.execution_count` from `.ipynb`, ignores `state.json` | False warnings, misleading output |
| `dasa profile notebook.ipynb --var df` fails with `NameError` after `dasa run` | `profile` replays cells with `execution_count is not None`, skips cells run via `dasa run` | Cannot profile after running cells |
| `dasa run --cell 5` fails when cells 1-4 were run via `dasa run` in a previous invocation | `run` replays prior cells by checking `execution_count`, misses cells without it | State not restored for downstream cells |
| `dasa check --fix` skips cells that need re-running | `_auto_fix` uses same `execution_count` check for replay | Fix mode doesn't work correctly |

### Important: Error handling & robustness

| # | Problem | File | Impact |
|---|---------|------|--------|
| 5 | Race condition in `state.json` — read-modify-write without locking | `session/state.py:26-30` | Concurrent `dasa run` processes can corrupt state |
| 6 | No error handling on file I/O — `json.load()`, `yaml.safe_load()`, `open()` all lack try/except | `session/state.py:24`, `session/context.py`, `session/profiles.py`, `notebook/jupyter.py:23` | Corrupted files crash CLI with unhelpful tracebacks |
| 7 | Notebook paths stored inconsistently — `"analysis.ipynb"` vs `"./analysis.ipynb"` vs absolute | `session/state.py:32` | Same notebook tracked as different entries |
| 8 | nbformat `MissingIDFieldWarning` — cells created without `id` fields | `notebook/jupyter.py` | Will become hard error in future nbformat versions |
| 9 | Dead code in `_print_deps_section()` — `dead_cells` computed but never displayed | `cli/check.py:196-200` | Unused code, missed feature |
| 10 | Empty notebook crash — `min()` on empty `cells_to_run` raises `ValueError` | `cli/run.py:53`, `cli/check.py:105` | Crash on empty or no-match cell selection |

### Minor: Code quality

| # | Problem | File | Impact |
|---|---------|------|--------|
| 11 | Kernel cleanup on start failure — `finally: shutdown()` errors if `start()` never succeeded | `cli/run.py:49`, `cli/profile.py:65` | Confusing secondary error |
| 12 | No cell index bounds checking — `get_cell(index)` raises raw `IndexError` | `notebook/jupyter.py:54` | Unclear error message |
| 13 | `--stale` doesn't respect dependency order — stale cells may depend on other stale cells | `cli/run.py:183-189` | Execution order violations |
| 14 | Missing return type hints on `_resolve_cells()` and session methods | Multiple files | Reduced type safety |

---

## Deliverables

| # | Deliverable | Description |
|---|-------------|-------------|
| 1 | Unified execution state | `check`, `profile`, `run` all consult `state.json` for cell execution status |
| 2 | Atomic file writes | `state.json` writes use temp-file-then-rename to prevent corruption |
| 3 | Robust file I/O | All session file reads wrapped in try/except with clear error messages |
| 4 | Path normalization | Notebook paths normalized before storing in `state.json` |
| 5 | Edge case hardening | Empty notebooks, bad cell indices, kernel start failures handled gracefully |
| 6 | Dead code activation | `dead_cells` detection displayed in `check` output |

---

## Tasks

### 6.1 Unified Execution State (Critical)

The core fix: make all commands consult `state.json` as the source of truth for cells executed via `dasa run`, falling back to notebook `execution_count` for cells executed in Jupyter/Colab.

**Design decision:** Do NOT write `execution_count` back to the `.ipynb` file. DASA should be non-invasive — it reads notebooks but doesn't mutate them unexpectedly. Instead, all commands check `state.json` alongside `execution_count`.

#### 6.1a Update `StateAnalyzer.analyze()` to consult `state.json`

**File:** `src/dasa/analysis/state.py`

```python
class StateAnalyzer:
    """Detect state inconsistencies in notebooks."""

    def analyze(self, adapter: NotebookAdapter, notebook_path: str | None = None) -> StateAnalysis:
        """Analyze notebook state consistency.
        
        Args:
            adapter: The notebook adapter.
            notebook_path: Path to notebook, used to check state.json for
                cells executed via `dasa run`. If None, only checks
                execution_count from the notebook file.
        """
        issues = []
        defined_vars: dict[str, int] = {}
        undefined_refs: list[tuple[int, str]] = []
        
        code_cells = adapter.code_cells
        
        # Load state.json tracking (cells executed via dasa run)
        state_tracker = StateTracker() if notebook_path else None

        # ... existing variable analysis ...

        # Check for never-executed cells — consult BOTH sources
        for cell in code_cells:
            executed_in_notebook = cell.execution_count is not None
            executed_via_dasa = (
                state_tracker is not None
                and not state_tracker.is_stale(notebook_path, cell.index, cell.source)
            )
            
            if not executed_in_notebook and not executed_via_dasa:
                issues.append(StateIssue(
                    cell_index=cell.index,
                    severity="warning",
                    message="never executed",
                ))
        
        # Check for stale cells (code changed since last run)
        if state_tracker and notebook_path:
            for cell in code_cells:
                if not state_tracker.is_stale(notebook_path, cell.index, cell.source):
                    continue  # Not stale or never run via dasa
                # Cell was run via dasa but code has changed since
                cell_state = state_tracker._get_cell_state(notebook_path, cell.index)
                if cell_state is not None:
                    issues.append(StateIssue(
                        cell_index=cell.index,
                        severity="warning",
                        message="stale — code modified since last `dasa run`",
                    ))

        # ... rest of analysis ...
```

#### 6.1b Update `profile` to replay cells from `state.json`

**File:** `src/dasa/cli/profile.py`

```python
# Replace the replay loop with one that consults state.json:

state_tracker = StateTracker()

for cell in adapter.code_cells:
    # Replay if executed in notebook OR via dasa run (and not stale)
    executed_in_notebook = cell.execution_count is not None
    executed_via_dasa = not state_tracker.is_stale(notebook, cell.index, cell.source)
    
    if executed_in_notebook or executed_via_dasa:
        result = kernel.execute(cell.source, timeout=60)
        if not result.success:
            console.print(
                f"[yellow]Warning: Cell {cell.index} failed during replay: "
                f"{result.error_type}: {result.error}[/yellow]"
            )
```

#### 6.1c Update `run` cell replay to consult `state.json`

**File:** `src/dasa/cli/run.py`

```python
# Replace the replay loop:

state_tracker_for_replay = StateTracker()

first_target = min(c.index for c in cells_to_run)
for c in code_cells:
    if c.index < first_target:
        executed_in_notebook = c.execution_count is not None
        executed_via_dasa = not state_tracker_for_replay.is_stale(
            notebook, c.index, c.source
        )
        if executed_in_notebook or executed_via_dasa:
            kernel.execute(c.source, timeout=timeout)
```

#### 6.1d Update `check --fix` to use same logic

**File:** `src/dasa/cli/check.py`

Same pattern: consult both `execution_count` and `state.json` when deciding which cells to replay and which need fixing.

---

### 6.2 Add helper method to `StateTracker`

**File:** `src/dasa/session/state.py`

Add a method to check if a cell was ever executed via `dasa run` (regardless of staleness):

```python
def was_executed(self, notebook: str, cell_index: int) -> bool:
    """Check if a cell was ever executed via dasa run."""
    state = self._load()
    nb_state = state.get(self._normalize_path(notebook), {}).get("cells", {})
    return str(cell_index) in nb_state

def _normalize_path(self, path: str) -> str:
    """Normalize notebook path for consistent state tracking."""
    return str(Path(path).resolve())

def _get_cell_state(self, notebook: str, cell_index: int) -> dict | None:
    """Get raw cell state for a specific cell, or None if never executed."""
    state = self._load()
    nb_state = state.get(self._normalize_path(notebook), {}).get("cells", {})
    return nb_state.get(str(cell_index))
```

---

### 6.3 Path Normalization

**File:** `src/dasa/session/state.py`

Normalize all notebook paths to absolute resolved paths before storing:

```python
def update_cell(self, notebook: str, cell_index: int, source: str) -> None:
    """Update the code hash for a cell after execution."""
    state = self._load()
    key = self._normalize_path(notebook)
    if key not in state:
        state[key] = {"cells": {}}
    
    code_hash = hashlib.sha256(source.encode()).hexdigest()[:12]
    state[key]["cells"][str(cell_index)] = {
        "code_hash": code_hash,
        "last_run": datetime.now().isoformat(),
    }
    self._save(state)
```

---

### 6.4 Atomic File Writes

**File:** `src/dasa/session/state.py`

Use temp-file-then-rename for crash safety:

```python
import tempfile

def _save(self, state: dict) -> None:
    """Save state to disk atomically."""
    self.state_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write to temp file, then rename (atomic on POSIX)
    fd, tmp_path = tempfile.mkstemp(
        dir=self.state_path.parent,
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(state, f, indent=2)
        os.replace(tmp_path, self.state_path)
    except:
        os.unlink(tmp_path)
        raise
```

Apply the same pattern to `context.py` and `profiles.py`.

---

### 6.5 Robust File I/O

Wrap all session file reads in try/except:

```python
# session/state.py
def _load(self) -> dict:
    """Load state from disk."""
    if not self.state_path.exists():
        return {}
    try:
        with open(self.state_path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        # Corrupted file — warn and start fresh
        import sys
        print(f"Warning: corrupted {self.state_path}, resetting: {e}", file=sys.stderr)
        return {}

# session/context.py — same pattern for yaml.safe_load()
# session/profiles.py — same pattern for yaml.safe_load()
# notebook/jupyter.py — wrap nbformat.read() with clear FileNotFoundError message
```

---

### 6.6 Edge Case Hardening

#### Empty cell list protection

**Files:** `src/dasa/cli/run.py`, `src/dasa/cli/check.py`

```python
# Before computing min() on cells_to_run:
if not cells_to_run:
    console.print("[yellow]No cells to run.[/yellow]")
    return
```

#### Cell index bounds checking

**File:** `src/dasa/notebook/jupyter.py`

```python
def get_cell(self, index: int) -> Cell:
    """Get cell by index."""
    if self._nb is None:
        raise ValueError("No notebook loaded")
    if index < 0 or index >= len(self._nb.cells):
        raise IndexError(
            f"Cell index {index} out of range (notebook has {len(self._nb.cells)} cells)"
        )
    # ... existing code ...
```

#### Kernel start failure

**Files:** `src/dasa/cli/run.py`, `src/dasa/cli/profile.py`, `src/dasa/cli/check.py`

```python
kernel = DasaKernelManager()
try:
    kernel.start()
except Exception as e:
    console.print(f"[red]Error: Failed to start kernel: {e}[/red]")
    console.print("[dim]Is ipykernel installed? Try: pip install ipykernel[/dim]")
    raise typer.Exit(1)

try:
    # ... execution logic ...
finally:
    kernel.shutdown()
```

#### Stale cells in dependency order

**File:** `src/dasa/cli/run.py`

```python
if stale_only:
    tracker = StateTracker()
    stale_indices = tracker.get_stale_cells(
        notebook,
        [(c.index, c.source) for c in code_cells],
    )
    # Sort by index to respect dependency order
    return [c for c in code_cells if c.index in stale_indices]
    # Already sorted since code_cells is in notebook order
```

---

### 6.7 Activate Dead Code Detection

**File:** `src/dasa/cli/check.py`

Display the `dead_cells` computation that's currently unused:

```python
# After computing dead_cells:
if dead_cells:
    dead_str = ", ".join(f"Cell {d}" for d in dead_cells)
    console.print(f"  [dim]Dead code (no downstream dependents): {dead_str}[/dim]")
```

---

## Acceptance Criteria

- [ ] `dasa run --all` followed by `dasa check` reports cells as executed (not "never executed")
- [ ] `dasa run --cell 1 && dasa run --cell 2` followed by `dasa profile --var df` successfully profiles
- [ ] `dasa run --cell 5` correctly replays cells 1-4 that were run via `dasa run` in a prior invocation
- [ ] `dasa check --fix` correctly identifies and re-runs stale cells
- [ ] Corrupted `state.json` doesn't crash the CLI — shows warning and resets
- [ ] Corrupted `context.yaml` doesn't crash the CLI — shows warning and resets
- [ ] `dasa run --cell 999` shows clear "out of range" error
- [ ] `dasa check empty.ipynb` works without crashing
- [ ] Notebook paths are normalized — `./nb.ipynb` and `nb.ipynb` reference same state
- [ ] `dead_cells` shown in `dasa check` output
- [ ] All 83 existing tests still pass
- [ ] New tests for state synchronization, path normalization, error handling

---

## Files Modified

```
src/dasa/
├── analysis/
│   └── state.py              # MODIFIED: consult state.json for execution status
├── cli/
│   ├── check.py              # MODIFIED: unified state, dead code display, edge cases
│   ├── profile.py            # MODIFIED: replay cells from state.json
│   └── run.py                # MODIFIED: replay from state.json, edge cases
├── notebook/
│   └── jupyter.py            # MODIFIED: bounds checking, error handling
└── session/
    ├── state.py              # MODIFIED: path normalization, atomic writes, helpers
    ├── context.py            # MODIFIED: robust file I/O
    └── profiles.py           # MODIFIED: robust file I/O
tests/
├── test_state_sync.py        # NEW: cross-command state synchronization tests
└── test_error_handling.py    # NEW: edge case and error handling tests
```

---

## Verification Plan

After implementing, run this exact sequence in `example/` to verify the critical fix:

```bash
cd example
rm -rf .dasa  # Clean slate

# 1. Run cells via dasa
dasa run analysis.ipynb --from 1 --to 3

# 2. Check should NOT report "never executed" for cells 1-3
dasa check analysis.ipynb
# Expected: cells 1-3 show as executed, cells 4+ show as "never executed"

# 3. Profile should work (replays cells 1-3 from state.json)
dasa profile analysis.ipynb --var df
# Expected: shows df profile (500 rows x 7 columns)

# 4. Run a later cell — should replay 1-3 automatically
dasa run analysis.ipynb --cell 5
# Expected: success (clean_df available from replayed cell 3)
```

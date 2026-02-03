# Sprint 4: State Tools

**Goal:** Implement state management tools: `vars`, `stale`, `kernel`.

**Duration:** ~2 days

**Prerequisite:** Sprint 3 (Execution tools)

---

## Deliverables

| # | Deliverable | Description |
|---|-------------|-------------|
| 1 | `dasa vars` | List variables in kernel memory |
| 2 | `dasa stale` | Find cells with outdated outputs |
| 3 | `dasa kernel` | Kernel management (status, restart, interrupt) |

---

## Tasks

### 4.1 Vars Command

```bash
dasa vars notebook.ipynb

# Output:
# Name          Type              Size      Defined    Used In
# ────────────────────────────────────────────────────────────
# df            DataFrame         4.6 MB    Cell 1     Cell 2,3,4
# clean_df      DataFrame         3.2 MB    Cell 2     Cell 3
# model         RandomForest      156 MB    Cell 4     Cell 5
```

**Features:**
- List all user-defined variables
- Show type, memory size
- Show which cell defined it
- Show which cells use it (from deps graph)

---

### 4.2 Stale Command

```bash
dasa stale notebook.ipynb

# Output:
# Stale cells (need re-run):
#   ⚠ Cell 2 (modified directly)
#   ⚠ Cell 3 (depends on Cell 2 via: clean_df)
#
# Up to date:
#   ✓ Cell 0, Cell 1, Cell 4
```

**Features:**
- Track cell code hash vs last execution hash
- Store state in `.dasa/state.json`
- Propagate staleness through dependency graph

---

### 4.3 Kernel Command

```bash
dasa kernel notebook.ipynb status
dasa kernel notebook.ipynb restart
dasa kernel notebook.ipynb interrupt
```

**Features:**
- Show kernel status (PID, memory, uptime)
- Restart kernel (clear all state)
- Interrupt running execution

---

## Acceptance Criteria

- [ ] `dasa vars` lists variables with metadata
- [ ] `dasa stale` detects modified cells
- [ ] `dasa kernel status` shows kernel info
- [ ] `dasa kernel restart` clears state
- [ ] State tracking persists to `.dasa/`

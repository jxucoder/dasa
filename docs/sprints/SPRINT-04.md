# Sprint 4: Multi-Agent & Hooks

**Goal:** Add multi-agent coordination patterns and auto-population hooks so the session stays current without manual effort.

**Duration:** ~3-4 days

**Prerequisite:** Sprint 3 (Hands + Memory: run + context)

**Informed by:** OpenCode's session hierarchy, Oh-My-OpenCode's hook system and agent roles.

---

## Deliverables

| # | Deliverable | Description |
|---|-------------|-------------|
| 1 | Agent roles in SKILL.md | Profiler, Executor, Analyst, Orchestrator role definitions |
| 2 | Auto-population hooks | Tools automatically update `.dasa/` session |
| 3 | Enhanced skill workflows | Multi-agent delegation patterns |
| 4 | Background execution | `dasa run --async` for long-running cells |
| 5 | Session coordination docs | Patterns for multi-agent data science |

---

## Design Rationale

### What we learned from OpenCode

OpenCode's multi-agent system works through **session hierarchy**: a parent session creates child sessions via the `task` tool, each with different agents and restricted permissions. The key patterns:

1. **Agents are configurations, not processes.** An agent is a name + model + prompt + permission ruleset.
2. **Permission boundaries prevent mistakes.** The `explore` agent physically cannot call `write`.
3. **Auto-population beats manual logging.** Oh-My-OpenCode hooks `PostToolUse` to inject context.
4. **The coordinator is optional.** One agent or many — the design supports both.

### How this maps to DASA

DASA doesn't manage agents — it provides tools. But it can define agent **roles** in the skill, enforce **permission boundaries** through tool design, and **auto-populate** the session so coordination happens through shared state.

---

## Tasks

### 4.1 Agent Roles in SKILL.md

Update the agent skill to define roles with clear boundaries:

```markdown
## Agent Roles

When working on a data science project with DASA, adopt one of these roles
based on the current task. Each role has specific tools and constraints.

### Profiler (read-only, use a fast model)

**When:** Understanding data, exploring notebook state, gathering information.

**Tools:** `dasa profile`, `dasa check`, `dasa context`
**Cannot:** Execute cells, modify notebook files
**Model guidance:** Use a fast/cheap model — this is mechanical exploration work.

Workflow:
1. `dasa context` — read project state
2. `dasa profile notebook.ipynb --var df` — profile each key variable
3. `dasa check notebook.ipynb` — assess notebook health
4. Report findings to orchestrator

### Executor (can execute, cannot edit)

**When:** Running cells, diagnosing errors, testing changes.

**Tools:** `dasa run`, `dasa profile`, `dasa check`, `dasa context`
**Cannot:** Modify notebook source code directly
**Model guidance:** Use a standard model — needs to understand error context.

Workflow:
1. `dasa context` — read project state
2. `dasa run notebook.ipynb --cell N` — execute and observe
3. If error: read context, fix the code, re-run
4. `dasa context --log "..."` — record outcome

### Analyst (read-only, use a smart model)

**When:** Strategic decisions, evaluating approaches, planning next steps.

**Tools:** `dasa check`, `dasa context`
**Cannot:** Execute cells, modify anything
**Model guidance:** Use the smartest available model — strategic reasoning needs intelligence.

Workflow:
1. `dasa context` — read full project history
2. Analyze approaches tried, results achieved
3. Recommend next steps based on evidence
4. `dasa context --log "..."` — record recommendation

### Orchestrator (delegates everything)

**When:** Complex multi-step tasks that need coordination.

**Tools:** All tools via delegation to specialist agents
**Model guidance:** Use the smartest model for planning, delegate execution to cheaper models.

Workflow:
1. `dasa context` — understand project state
2. Decide what needs to happen next
3. Delegate profiling to a profiler agent
4. Delegate execution to an executor agent
5. Review results, decide next step
6. `dasa context --set-status "..."` — update project status
```

---

### 4.2 Auto-Population Hooks

Make every DASA tool automatically update the session. No manual logging needed.

#### Profile auto-cache

When `dasa profile --var df` runs successfully:
1. Save profile to `.dasa/profiles/df.yaml`
2. Append to `.dasa/log`: `"Profiled df. 50k rows x 12 cols. Issues: age 4.7% null"`

```python
# In profile command, after successful profiling:
def _auto_update_session(profile: DataFrameProfile):
    """Auto-update session after profiling."""
    # Cache profile
    cache = ProfileCache()
    cache.save(profile.name, profile.to_dict())
    
    # Log
    log = SessionLog()
    issues_str = ", ".join(profile.issues[:3]) if profile.issues else "none"
    log.append("profile", 
        f"Profiled {profile.name}. "
        f"{profile.shape[0]:,} rows x {profile.shape[1]} cols. "
        f"Issues: {issues_str}")
```

#### Check auto-log

When `dasa check notebook.ipynb` runs:
1. Append to `.dasa/log`: summary of findings

```python
def _auto_update_session(analysis: StateAnalysis, notebook: str):
    log = SessionLog()
    error_count = sum(1 for i in analysis.issues if i.severity == "error")
    warning_count = sum(1 for i in analysis.issues if i.severity == "warning")
    
    if error_count:
        log.append("check", f"{notebook}: {error_count} errors, {warning_count} warnings")
    else:
        log.append("check", f"{notebook}: consistent ({warning_count} warnings)")
```

#### Run auto-log + state update

When `dasa run --cell N` executes:
1. Update `.dasa/state.json` with new code hash and timestamp
2. Append to `.dasa/log`: success or failure with error type

```python
def _auto_update_session(cell_index: int, result: ExecutionResult, notebook: str):
    # Update state hash
    state = StateTracker()
    state.update_cell(notebook, cell_index, cell_source)
    
    # Log
    log = SessionLog()
    if result.success:
        log.append("run", f"Cell {cell_index} executed (success, {result.execution_time:.1f}s)")
    else:
        log.append("run", f"Cell {cell_index} failed: {result.error_type}: {result.error}")
```

---

### 4.3 Background Execution

Add `--async` flag to `dasa run` for long-running cells.

```bash
# Start long operation in background
dasa run notebook.ipynb --cell 4 --async
# Output: Started job abc123. Check with: dasa status abc123

# Check progress
dasa status abc123
# Output: RUNNING (45s elapsed)

# When done
dasa status abc123
# Output: COMPLETED (success, 127s)
```

**Implementation:**
- Jobs tracked in `.dasa/jobs/{id}.json`
- Background process via `subprocess`
- Polling for status via job file

```python
@dataclass
class Job:
    id: str
    notebook: str
    cell: int
    pid: int
    status: str  # "running", "completed", "failed"
    started_at: str
    completed_at: Optional[str]
    result: Optional[dict]
```

---

### 4.4 Multi-Agent Coordination Patterns

Document coordination patterns for different platforms:

#### Pattern 1: Sequential (any platform)

```
Conversation 1 (exploration):
  Agent: dasa context  →  no context yet
  Agent: dasa profile notebook.ipynb --var df  →  sees data
  Agent: dasa check notebook.ipynb  →  sees state
  Agent: dasa context --set-goal "Predict churn" --log "Profiled data, 50k rows"

Conversation 2 (execution):
  Agent: dasa context  →  reads goal, data profiles, previous log
  Agent: writes code using correct column names (from cached profile)
  Agent: dasa run --cell 5  →  executes
  Agent: dasa context --log "Trained logistic regression, 0.84 AUC"
```

#### Pattern 2: Parallel (OpenCode / agent platforms with task tool)

```
Orchestrator:
  dasa context  →  reads state
  Decides: need profiling + code fix

  Spawns child session → Profiler agent:
    dasa profile notebook.ipynb --var df
    dasa profile notebook.ipynb --var model
    (auto-caches to .dasa/profiles/)

  Spawns child session → Executor agent:
    dasa run notebook.ipynb --cell 8
    Reads error, fixes code
    dasa run notebook.ipynb --cell 8  →  success
    (auto-logs to .dasa/log)

  Orchestrator reads updated .dasa/ session
  Both agents' work is visible through shared state
```

#### Pattern 3: Human + Agent

```
Human:
  dasa context --set-goal "Predict churn, AUC > 0.80"
  dasa context --log "Must be interpretable for stakeholders"

Agent (any conversation):
  dasa context  →  reads human's goal and constraints
  Works toward the goal with full context
  dasa context --log "Tried random forest, overfit"

Human (later):
  dasa context  →  sees what agent tried
  dasa context --log "Good direction, try adding feature X"

Agent (next conversation):
  dasa context  →  sees human's feedback
  Continues with adjusted approach
```

---

## Acceptance Criteria

- [ ] Agent skill defines Profiler, Executor, Analyst, Orchestrator roles
- [ ] `dasa profile` auto-caches to `.dasa/profiles/`
- [ ] `dasa check` auto-logs findings
- [ ] `dasa run` auto-logs results and updates state hash
- [ ] `dasa run --async` backgrounds execution
- [ ] `dasa status` shows job progress
- [ ] Multi-agent coordination patterns documented in skill
- [ ] All auto-population hooks tested

---

## Files Created/Modified

```
src/dasa/
├── cli/
│   └── status.py          # NEW: async job status
├── session/
│   ├── jobs.py             # NEW: async job tracking
│   └── state.py            # NEW: staleness tracking (.dasa/state.json)
skills/
└── notebook/
    └── SKILL.md            # UPDATED: agent roles + workflows
```

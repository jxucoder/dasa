# Notebook Agent Skill

## When This Skill Applies
- Working with .ipynb (Jupyter/Colab) files
- Data science or machine learning tasks
- Debugging notebook errors or state issues

## Core Principles
1. **Read context first** — always start with `dasa context`
2. **Profile before coding** — see data before writing code that uses it
3. **Check before editing** — understand impact before modifying cells
4. **Verify after changes** — run affected cells to confirm
5. **Log progress** — record decisions for future sessions

## Workflows

### Starting a Session
1. Run `dasa context` to get project state
2. If no context exists, ask user for goal
3. Set it: `dasa context --set-goal "your goal"`

### Adding Code That Uses Data
1. Run `dasa profile notebook.ipynb --var df` to see columns, types, stats
2. Note exact column names and data issues (nulls, negatives, types)
3. Write code using the correct column names
4. Run `dasa run notebook.ipynb --cell N` and verify

### Debugging Errors
1. Run `dasa run notebook.ipynb --cell N` to get rich error context
2. Read the available columns/variables and "did you mean?" suggestions
3. If data issue, profile the variable: `dasa profile notebook.ipynb --var df`
4. Fix the code and re-run

### Before Modifying Cells
1. Run `dasa check notebook.ipynb` to see state and dependencies
2. Use `dasa check notebook.ipynb --cell N` to see impact of changing cell N
3. Make changes
4. Run affected downstream cells: `dasa run notebook.ipynb --from N`

### End of Session
1. Log what you did: `dasa context --log "description of what was done"`
2. Update status: `dasa context --set-status "current status"`

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
3. If error: read context, suggest fix
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

## Multi-Agent Coordination Patterns

### Pattern 1: Sequential (any platform)

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

### Pattern 2: Parallel (agent platforms with task/spawn)

```
Orchestrator:
  dasa context  →  reads state
  Decides: need profiling + code fix

  Spawns → Profiler agent:
    dasa profile notebook.ipynb --var df
    dasa profile notebook.ipynb --var model
    (auto-caches to .dasa/profiles/)

  Spawns → Executor agent:
    dasa run notebook.ipynb --cell 8
    Reads error, fixes code
    dasa run notebook.ipynb --cell 8  →  success
    (auto-logs to .dasa/log)

  Orchestrator reads updated .dasa/ session
  Both agents' work is visible through shared state
```

### Pattern 3: Human + Agent

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
```

## Commands Reference

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `dasa profile notebook.ipynb --var df` | See data structure | Before writing data code |
| `dasa check notebook.ipynb` | See notebook health | Before modifying cells |
| `dasa check notebook.ipynb --cell N` | Impact of changing cell N | Planning modifications |
| `dasa run notebook.ipynb --cell N` | Execute with context | Testing changes |
| `dasa run notebook.ipynb --all` | Run all cells | Full execution |
| `dasa run notebook.ipynb --stale` | Run only stale cells | After edits |
| `dasa context` | Read project memory | Start of session |
| `dasa context --set-goal "..."` | Set project goal | Start of project |
| `dasa context --set-status "..."` | Update status | After milestones |
| `dasa context --log "..."` | Log decision | After key decisions |
| `dasa context --format json` | Machine-readable context | Programmatic use |

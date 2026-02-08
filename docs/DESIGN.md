# DASA Design

## The Problem

A data scientist is working in a Jupyter notebook. They ask their AI assistant:

> "Add a bar chart of revenue by region"

The AI writes:

```python
plt.bar(df['region'], df['revenue_usd'])
```

It fails. The column is called `revenue`, not `revenue_usd`. The AI had no way to know — it can read the notebook file, but it can't see the data.

They try again:

> "My model accuracy dropped, can you help?"

The AI looks at the notebook, sees a model training cell, and suggests retraining with different hyperparameters. But the real problem was that cell 3 (data cleaning) was modified and never re-run, so the model is training on dirty data. The AI can't see kernel state — it doesn't know cell 3 is stale.

Next day, new conversation:

> "Continue working on the churn model"

The AI has no memory. It doesn't know they spent yesterday trying random forest (overfit), settled on logistic regression (0.84 AUC), and were about to try adding a `days_inactive` feature. The data scientist has to re-explain everything.

**These are not edge cases. This is the default experience of using AI assistants for data science work today.**

---

## Why Agents Fail at Notebooks

A notebook is the worst possible environment for an AI agent. Here's why:

**The file lies.** In a `.py` file, the code IS the truth. In a notebook, the code might not reflect what's actually in memory. Variables can exist that no cell defines. Outputs can be from hours ago. Cells can depend on deleted code. The `.ipynb` file is a snapshot of what was *written*, not what *happened*.

**The data is invisible.** The agent can see code like `df.dropna()`, but it doesn't know what `df` looks like — how many rows, what columns, what types, where the nulls are. To write correct code, you need to see the data. The agent is coding blind.

**Context evaporates.** Every conversation starts from scratch. The agent doesn't know:
- What the goal is
- What was already tried
- Why certain approaches were abandoned
- Where the analysis left off

A human colleague sitting next to you would know all of this. An AI assistant knows none of it.

**Expensive operations are invisible.** The agent doesn't know that cell 4 takes 2 hours to run. It might casually re-execute it. Or suggest changes that invalidate a cached model training run.

---

## What Data Scientists Actually Want

Not a new notebook format. Not a protocol. Not an architecture diagram.

They want: **An AI assistant that understands their data science work as well as a human colleague would.**

A human colleague can:
- See the data ("that DataFrame has 50k rows and a `revenue` column")
- See the notebook state ("your output is stale, you changed the code")
- Remember context ("yesterday you tried random forest and it overfit")
- Work safely ("don't re-run the training cell, it takes 2 hours")

An AI assistant today can do none of these. DASA closes that gap.

---

## The Design: Eyes, Memory, Hands

Three capabilities, each solving a specific failure mode.

### Eyes — See what's really there

The agent needs to see things the notebook file doesn't show:

| What's invisible | What the agent needs | DASA tool |
|---|---|---|
| Data shape and content | Column names, types, stats, quality issues | `dasa profile` |
| Kernel state | What variables exist, what's stale, dependencies | `dasa check` |
| Execution safety | What's cheap, what's expensive, what depends on what | `dasa check` |

### Memory — Remember across conversations

The agent needs persistent context that survives between conversations:

| What's forgotten | What should persist | Stored in |
|---|---|---|
| Project goal | "Predict churn, AUC > 0.80, must be interpretable" | `.dasa/context.yaml` |
| Data knowledge | Cached profiles — schema, stats, quality | `.dasa/profiles/` |
| What was tried | "Random forest overfit, switched to LR" | `.dasa/log` |
| Current status | "Features done, training next" | `.dasa/context.yaml` |

### Hands — Act safely in the notebook

The agent needs to execute with awareness:

| What goes wrong | What the agent needs | DASA tool |
|---|---|---|
| Code fails with no context | Rich errors with data context, suggestions | `dasa run` |
| Expensive cells re-run | Cost awareness, dependency-aware execution | `dasa run` |
| Changes break downstream | Verify notebook still works end-to-end | `dasa run --check` |

---

## Four Commands

Not sixteen. Four.

### `dasa profile`

See the data.

```
$ dasa profile notebook.ipynb --var df

DataFrame: df (50,000 rows × 12 columns)

  user_id       int64      50,000 unique, no nulls
  age           int64      min=18, max=95, mean=42
                           ⚠ 2,341 nulls (4.7%)
  score         float64    min=0.0, max=1.0, mean=0.65
  region        object     4 unique: [North, South, East, West]
  churned       int64      values: [0, 1], mean=0.23

Issues:
  ⚠ age: 4.7% null values
```

The agent now knows exactly what columns exist, their types, and their content. It won't write `df['revenue_usd']` when the column is `df['revenue']`.

**Side effect:** Automatically saves the profile to `.dasa/profiles/df.yaml`. Next time any agent needs to know about `df`, it can read the cached profile instantly — no kernel needed.

### `dasa check`

See the notebook health.

```
$ dasa check notebook.ipynb

Notebook: analysis.ipynb (24 cells, kernel running)

State:
  ⚠ Cell 3: output is STALE (code modified after last run)
  ⚠ Cell 8: uses variable 'X' which may not exist
  ✓ 22 cells consistent

Dependencies:
  Cell 0 (imports) → all cells
  Cell 1 (load) → Cell 2, 3, 5, 8
  Cell 5 (features) → Cell 8, 12

  If you modify Cell 1: 8 cells need re-run

Pipeline: [0] → [1] → [2] → [3] → [5] → [8] → [12]
Dead code: Cells 4, 6, 7, 9, 10, 11 (no downstream dependents)
```

One command that gives the agent a complete picture of the notebook. Combines state validation, dependency analysis, and staleness detection.

### `dasa run`

Execute cells with awareness.

```
$ dasa run notebook.ipynb --cell 5

Cell 5 executed (0.3s)

Output:
  X shape: (47500, 3), y shape: (47500,)
  Features: age, score, days_inactive

⚠ Downstream cells may be stale: Cell 8, Cell 12
  Run `dasa run notebook.ipynb --from 8` to update
```

When a cell fails:

```
$ dasa run notebook.ipynb --cell 8

Cell 8 FAILED (0.1s)

Error: KeyError: 'revenue_usd'
  Line 3: df['profit'] = df['revenue_usd'] - df['cost']

Available columns: user_id, age, score, region, revenue, cost
Did you mean: 'revenue'?
```

The agent gets the error, the context, and a suggestion — all in one output.

### `dasa context`

Read and write project memory.

```
$ dasa context

Project: churn_prediction
Goal: Predict user churn, AUC > 0.80, interpretable model
Status: features complete, model training next
Notebook: analysis.ipynb

Data:
  df: 50,000 rows × 12 cols (users.csv)
  Target: churned (23% positive rate)

Tried:
  ✗ Random forest — overfit (0.91 train / 0.72 test)
  ✗ XGBoost — marginal improvement, slow
  ✓ Logistic regression — 0.84 test AUC (current best)

Recent:
  [10:00] Set goal: predict churn, interpretable
  [10:15] Profiled data. 50k rows, nulls in age (4.7%)
  [10:30] Random forest overfit. Switching to LR.
  [11:00] LR: 0.84 AUC. Adding days_inactive feature next.
```

Any agent, in any conversation, reads this and has full context in one shot.

To update:

```
$ dasa context --set-goal "Predict user churn, AUC > 0.80"
$ dasa context --log "Tried adding days_inactive feature. AUC improved to 0.86."
$ dasa context --set-status "evaluation"
```

---

## The Session

The session is a `.dasa/` directory that accumulates project knowledge. It's the key innovation — the thing that makes everything else 10x more useful.

```
.dasa/
├── context.yaml          # Goal, status, constraints
├── profiles/             # Cached data profiles
│   ├── df.yaml
│   └── df_clean.yaml
└── log                   # Decision history (append-only)
```

### context.yaml

```yaml
project:
  name: churn_prediction
  goal: Predict user churn with AUC > 0.80
  constraints:
    - Model must be interpretable (stakeholder requirement)
    - Inference under 100ms (production constraint)
  status: evaluation
  notebook: analysis.ipynb

data:
  primary: data/users.csv
  rows: 50000
  target: churned
  target_rate: 0.23

approaches:
  - name: random_forest
    result: "0.91 train / 0.72 test"
    status: abandoned
    reason: overfit badly
  - name: logistic_regression
    result: "0.86 test AUC"
    status: current
    reason: good generalization, interpretable
```

### profiles/df.yaml

```yaml
name: df
shape: [50000, 12]
profiled_at: 2026-02-08T10:15:00
source: data/users.csv

columns:
  user_id:   {dtype: int64, unique: 50000, nulls: 0}
  age:       {dtype: int64, min: 18, max: 95, mean: 42, nulls: 2341}
  score:     {dtype: float64, min: 0.0, max: 1.0, mean: 0.65, nulls: 150}
  region:    {dtype: object, unique: 4, top_values: [North, South, East, West]}
  churned:   {dtype: int64, values: [0, 1], mean: 0.23}

issues:
  - "age: 2,341 nulls (4.7%)"
  - "score: 150 nulls (0.3%)"
```

### log

```
2026-02-08 10:00 [user] Goal: predict churn, need interpretable model
2026-02-08 10:15 [agent] Profiled df. 50k rows, 23% churn rate. Nulls in age (4.7%)
2026-02-08 10:25 [agent] Dropped null rows. 47.5k remain
2026-02-08 10:45 [agent] Random forest: 0.91 train / 0.72 test. Overfit. Abandoning
2026-02-08 11:00 [agent] Logistic regression: 0.84 test AUC. Better generalization
2026-02-08 11:20 [agent] Added days_inactive feature. AUC improved to 0.86
2026-02-08 11:30 [user] Good enough for v1. Let's evaluate and save
```

### How the session works

**Tools update it automatically.** When you run `dasa profile --var df`, the profile is cached in `.dasa/profiles/df.yaml`. When `dasa run` executes a cell, the outcome is appended to `.dasa/log`. No extra step needed.

**Agents read it at the start of every conversation.** The first thing an agent does is `dasa context` — now it has full project knowledge.

**Both humans and agents write to it.** The human sets the goal. The agent logs what it tried. The next agent (or human) sees everything.

**It's just files.** YAML and plain text. Versionable with git. Readable by any tool. No database, no server, no special infrastructure.

---

## Multi-Agent Architecture

Multi-agent isn't a separate feature. It emerges naturally from the session — and from a pattern we learned by studying OpenCode and Oh-My-OpenCode.

### The Pattern: Shared Session, Specialized Agents

The most effective multi-agent systems don't use complex coordination protocols. They use **shared state with role-based agents**. OpenCode's multi-agent architecture works through parent-child sessions where:

1. A coordinator agent reads shared state and decides what to do
2. Specialized agents execute bounded tasks with restricted permissions
3. All agents read and write the same shared state
4. The session accumulates knowledge across all agent interactions

DASA applies this pattern to data science:

```
                      ┌─────────────────────┐
                      │   Orchestrator       │
                      │   (main agent)       │
                      │                      │
                      │   Reads .dasa/       │
                      │   Decides next step  │
                      └──────────┬───────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                   │
    ┌─────────▼─────────┐ ┌─────▼──────────┐ ┌─────▼──────────┐
    │   Profiling Agent  │ │ Execution Agent│ │ Analysis Agent │
    │                    │ │                │ │                │
    │   dasa profile     │ │ dasa run       │ │ dasa check     │
    │   dasa check       │ │                │ │ dasa context   │
    │                    │ │                │ │                │
    │   Read-only.       │ │ Can execute.   │ │ Read-only.     │
    │   Cannot edit.     │ │ Cannot edit.   │ │ Cannot edit.   │
    └────────┬───────────┘ └──────┬─────────┘ └──────┬─────────┘
             │                    │                   │
             └──────────────────┬─┘───────────────────┘
                                │
                      ┌─────────▼───────────┐
                      │   .dasa/ session     │
                      │                      │
                      │   context.yaml       │
                      │   profiles/          │
                      │   log                │
                      └─────────────────────┘
```

### Agent Roles

Different agents need different capabilities. Like OpenCode restricts its `explore` agent to read-only tools, DASA defines roles with permission boundaries:

| Role | Tools Available | Can Execute? | Can Edit Notebook? | Purpose |
|------|----------------|-------------|-------------------|---------|
| **Profiler** | `profile`, `check` | No | No | Understand data and state |
| **Executor** | `run`, `profile`, `check` | Yes | No | Run cells, diagnose errors |
| **Analyst** | `check`, `context` | No | No | Assess state, plan next steps |
| **Orchestrator** | All (via delegation) | Via delegation | Via delegation | Coordinate work |

The profiler agent can never accidentally execute a 2-hour training cell. The executor can run cells but can't delete them. The orchestrator delegates to specialists.

### How It Works in Practice

**Single agent (today):**

```
1. Agent reads .dasa/context.yaml → full project context
2. Agent calls dasa profile --var df → sees data
3. Agent calls dasa check notebook.ipynb → sees state
4. Agent writes code, calls dasa run --cell 5 → executes
5. dasa auto-updates .dasa/profiles/ and .dasa/log
6. Conversation ends, context persists
7. Next conversation → agent calls dasa context, picks up where it left off
```

**Multiple agents (tomorrow):**

```
1. Coordinator reads .dasa/context.yaml → understands status
2. Coordinator decides: "need feature engineering and hyperparameter tuning"
3. Agent A (profiler): reads session, profiles new features, updates .dasa/profiles/
4. Agent B (executor): reads session, trains model, updates .dasa/log
5. Coordinator reads updated session, compares results, decides next step
```

**The only coordination mechanism is the shared session.** Agent A doesn't talk to Agent B. They both read and write the same `.dasa/` directory. This is the same pattern that makes OpenCode's parent-child sessions work.

### Why This Works

Lessons from studying OpenCode and Oh-My-OpenCode's architectures:

1. **Session hierarchy over message passing.** OpenCode coordinates agents through parent-child sessions sharing a storage layer, not through direct inter-agent communication. DASA's `.dasa/` directory is the equivalent.

2. **Permission boundaries prevent mistakes.** OpenCode's `explore` agent physically cannot call `write` or `edit`. DASA's profiling agents physically cannot execute cells. Constraints are enforced by the tool, not by instructions.

3. **Auto-population beats manual logging.** Oh-My-OpenCode hooks `PostToolUse` to automatically inject context. DASA tools automatically update the session — `profile` caches results, `run` logs outcomes, `check` records state.

4. **The coordinator is optional.** For simple tasks, one agent reads the session and does the work. For complex tasks, a coordinator reads the session and delegates. The design supports both without changes.

5. **Cheap models for exploration, expensive models for reasoning.** Oh-My-OpenCode uses Claude Haiku for search and Claude Opus for orchestration. DASA's profiling/checking is cheap mechanical work; diagnosis and fixing need intelligence.

---

## What We Don't Build

### A new notebook format

We explored this (see [FORMAT.md](FORMAT.md) for the thinking). The problems aren't in the format — they're in the agent's lack of context. Adding context via tools + session solves the problems without requiring anyone to change formats.

### A complex coordination protocol

We studied blackboard architectures and multi-agent message-passing systems. Shared files are simpler. The session gives agents shared memory without any protocol. If coordination becomes a bottleneck at scale, add protocol then.

### Cell manipulation commands

The original plan included `add`, `edit`, `delete`, `move` commands. But agents can already edit `.ipynb` files — it's just JSON. The value of DASA is things agents *can't* do by reading the file: see kernel state, profile data, understand dependencies.

### An agent orchestrator

DASA is a **toolkit**, not a platform. It provides tools that any agent can use — in Cursor, Claude Code, OpenCode, or any other environment. The orchestration layer belongs to the platform (OpenCode's session hierarchy, Cursor's agent mode, etc.). DASA provides the data science-specific capabilities that these platforms lack.

---

## What's Next

**Build the eval first** (Sprint 0 — unchanged). The eval framework tells us whether any of this actually helps.

**Then build the session** (Sprint 1). The `.dasa/` directory is the foundation that makes every subsequent tool more valuable.

**Then build the eyes** (Sprint 2 — profile + check). Agents can see data and notebook state.

**Then build the hands and memory** (Sprint 3 — run + context). Agents can execute safely and remember across conversations.

**Then measure.** Does an agent with eyes + memory + hands perform measurably better than an agent without? The eval tells us.

**Then build multi-agent support** (Sprint 4). Agent roles, hook system for auto-population, background execution patterns.

**Then extend** (Sprint 5). MCP server for direct integration. Marimo adapter. Replay for reproducibility.

If an agent with eyes + memory + hands performs dramatically better — and I believe it will — then we have an open source toolkit that makes any AI agent significantly better at data science work. Not by changing what data scientists use, but by giving their AI assistants the context they've been missing.

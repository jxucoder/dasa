# DASA: Diagnostic Tools for Notebook Agents

> **D**ata science **A**gent **S**kill and diagnostic toolkit for **A**gents

DASA helps coding agents (Cursor, Claude Code, OpenCode, Codex) work effectively with Python notebooks by providing diagnostic tools that solve the fundamental problems of notebook development.

## The Problem

Data science notebooks have issues that coding agents can't handle with standard file operations:

| Problem | Impact |
|---------|--------|
| **Hidden state** | 36% of Jupyter notebooks don't reproduce |
| **Out-of-order execution** | Output doesn't match code |
| **Unknown data** | Agent writes code for data it hasn't seen |
| **Long-running cells** | Agent times out waiting for training |
| **Lost context** | Knowledge evaporates between conversations |

**Regular coding agents can read and write files. They can't diagnose notebook state.**

## The Solution

Four commands that give agents eyes, hands, and memory for notebook work:

```bash
# See the data
dasa profile notebook.ipynb --var df

# See the notebook health
dasa check notebook.ipynb

# Execute cells with rich error context
dasa run notebook.ipynb --cell 5

# Read/write persistent project memory
dasa context
```

Plus an **Agent Skill** (`SKILL.md`) that teaches agents when and how to use these tools.

## Quick Start

```bash
# Install
pip install dasa

# Profile a DataFrame
dasa profile my_analysis.ipynb --var df

# Check notebook health
dasa check my_analysis.ipynb

# Run a cell with error context
dasa run my_analysis.ipynb --cell 3

# Read project context
dasa context
```

## Commands

### `dasa profile` — See the data

```
$ dasa profile notebook.ipynb --var df

DataFrame: df (50,000 rows x 12 columns)
Memory: 4.6 MB

Column      Type       Non-Null     Unique   Stats / Values              Issues
---
user_id     int64      50,000 (100%) 50,000  min=1, max=50000
age         int64      47,659 (95%)  78      min=18, max=95, mean=42     4.7% null
revenue     float64    48,750 (98%)  12,341  min=-500, max=99847         2.5% null, 23 negative
region      object     50,000 (100%) 4       'North', 'South', 'East'
```

Auto-caches the profile to `.dasa/profiles/df.yaml` for instant reuse.

### `dasa check` — See notebook health

```
$ dasa check notebook.ipynb

Notebook: analysis.ipynb (24 cells)

State:
  X Cell 3: output is STALE (code modified after last run)
  X Cell 8: uses undefined variable 'X'
  ! Cell 10: never executed
  OK 21 cells consistent

Dependencies:
  Cell 0 (imports) -> Cell 1, 2, 3, 4, 5
  Cell 1 (df = pd.read_csv...) -> Cell 2, 3, 5, 8

  If you modify Cell 1: 6 cells need re-run -> [2, 3, 5, 8, 12]
```

One command combining state validation, dependency analysis, and staleness detection.

### `dasa run` — Execute safely

```
$ dasa run notebook.ipynb --cell 8

Cell 8 FAILED (0.1s)

Error: KeyError: 'revenue_usd'
  Line 3: df['profit'] = df['revenue_usd'] - df['cost']

Available columns: user_id, age, score, region, revenue, cost
Suggestion: Did you mean 'revenue'?
```

Rich error context with available variables and "did you mean?" suggestions.

### `dasa context` — Remember across conversations

```
$ dasa context

Project: churn_prediction
Goal: Predict user churn, AUC > 0.80, interpretable model
Status: features complete, model training next

Data:
  df: 50,000 rows x 12 cols (users.csv)

Tried:
  X Random forest -- overfit (0.91 train / 0.72 test)
  OK Logistic regression -- 0.84 test AUC (current best)

Recent:
  [10:00] Set goal: predict churn, interpretable
  [10:15] Profiled data. 50k rows, nulls in age (4.7%)
  [11:00] LR: 0.84 AUC. Adding days_inactive feature next.
```

Persistent project memory that survives between conversations.

## The Session

The `.dasa/` directory accumulates project knowledge automatically:

```
.dasa/
  context.yaml          # Goal, status, constraints
  profiles/             # Cached data profiles (auto-populated)
    df.yaml
  log                   # Decision history (append-only)
  state.json            # Cell execution hashes (staleness)
```

Tools auto-populate it: `profile` caches results, `run` logs outcomes, `check` records findings. Any agent reads `dasa context` to get full project state.

---

## Using DASA with Cursor

### 1. Install DASA in your project

```bash
pip install dasa
```

Or with `uv`:

```bash
uv add dasa
```

### 2. Add the Agent Skill

Copy the DASA skill into your Cursor rules so the agent knows when and how to use DASA tools:

```bash
# Create the rules directory if it doesn't exist
mkdir -p .cursor/rules

# Copy the skill
cp skills/notebook/SKILL.md .cursor/rules/dasa-notebook.md
```

Alternatively, add DASA to your project's `AGENTS.md`:

```markdown
## Notebook Work

When working with .ipynb files, use DASA tools:

1. `dasa context` — read project state before starting
2. `dasa profile notebook.ipynb --var df` — see data before writing code
3. `dasa check notebook.ipynb` — check health before editing cells
4. `dasa run notebook.ipynb --cell N` — execute with rich error context
5. `dasa context --log "..."` — record progress when done
```

### 3. How the agent uses it

Once the skill is installed, the Cursor agent will automatically:

- Run `dasa context` at the start of each session to pick up where you left off
- Run `dasa profile --var df` before writing code that uses DataFrames, so it uses the correct column names
- Run `dasa check` before modifying cells to understand dependencies
- Run `dasa run --cell N` to test changes with rich error context ("Did you mean 'revenue'?")
- Run `dasa context --log "..."` to record decisions for the next session

### Example conversation

```
You: Fix the error in cell 8 of analysis.ipynb

Agent: (runs dasa context → reads project state)
Agent: (runs dasa check analysis.ipynb → sees cell 8 uses undefined 'results')
Agent: (runs dasa run analysis.ipynb --cell 8 → gets NameError with available variables)
Agent: (fixes the code, re-runs → success)
Agent: (runs dasa context --log "Fixed cell 8: added results aggregation")
```

---

## Using DASA with Claude Code

### 1. Install DASA

```bash
pip install dasa
```

### 2. Add the Agent Skill

```bash
# Create the skills directory
mkdir -p .claude/skills/notebook

# Copy the skill
cp skills/notebook/SKILL.md .claude/skills/notebook/SKILL.md
```

Or add to your `CLAUDE.md`:

```markdown
## Notebook Work

When working with .ipynb files, always use DASA tools:

- `dasa context` — read project state at start
- `dasa profile notebook.ipynb --var df` — see data before writing code
- `dasa check notebook.ipynb` — understand dependencies before editing
- `dasa run notebook.ipynb --cell N` — execute with rich error context
- `dasa context --log "..."` — record progress at end
```

### 3. Multi-conversation workflow

DASA's context system is designed for Claude Code's conversation model. Context persists in `.dasa/context.yaml` across separate conversations:

```
Conversation 1 (exploration):
  Agent: dasa context                    → no context yet
  Agent: dasa profile notebook.ipynb     → sees data
  Agent: dasa check notebook.ipynb       → sees state issues
  Agent: dasa context --set-goal "Predict churn"
  Agent: dasa context --log "Profiled data, 50k rows, nulls in age"

Conversation 2 (implementation):
  Agent: dasa context                    → reads goal, profiles, previous log
  Agent: writes code using correct column names (from cached profile)
  Agent: dasa run --cell 5               → executes and verifies
  Agent: dasa context --log "Trained LR model, 0.84 AUC"

Conversation 3 (iteration):
  Agent: dasa context                    → sees full history
  Agent: knows what was tried, what worked, what to do next
```

---

## Using DASA with Any Agent

DASA is CLI-first — any agent that can run bash commands can use it. The workflow is the same:

| Step | Command | Purpose |
|------|---------|---------|
| Start | `dasa context` | Read project state |
| Before data code | `dasa profile --var df` | See exact columns, types, stats |
| Before editing | `dasa check notebook.ipynb` | Understand dependencies |
| Debug errors | `dasa run --cell N` | Rich error context |
| End of session | `dasa context --log "..."` | Record progress |

### Supported agents

| Agent | Skill Location | Notes |
|-------|---------------|-------|
| **Cursor** | `.cursor/rules/dasa-notebook.md` | Add as workspace rule |
| **Claude Code** | `.claude/skills/notebook/SKILL.md` | Add as skill |
| **OpenCode** | Reference in system prompt | Works via bash tool |
| **Codex** | Reference in instructions | Works via bash tool |
| **Aider** | Reference in `.aider.conf.yml` | Works via shell commands |
| **Any MCP client** | `dasa mcp-serve` | Direct tool integration (experimental) |

---

## Try It

An example workspace is included to try all four commands:

```bash
cd example

# Check notebook health (finds bugs + dependencies)
dasa check analysis.ipynb

# Profile the data (no kernel needed)
dasa profile --file data/sales.csv

# Run cells and see rich error context
dasa run analysis.ipynb --cell 1
dasa run analysis.ipynb --cell 4    # → KeyError, "Did you mean 'revenue'?"

# Set up project memory
dasa context --set-goal "Analyze sales"
dasa context --log "Found revenue_usd bug, should be revenue"
dasa context                         # Read it back
```

See `example/README.md` for a full walkthrough.

## Documentation

- [Design](docs/DESIGN.md) — Vision, problem, solution, multi-agent architecture
- [Architecture](docs/ARCHITECTURE.md) — Technical components, session system, package structure
- [Plan](docs/PLAN.md) — Sprint roadmap (7 sprints, MVP = Sprints 0-3)
- [Evaluation](docs/EVAL.md) — Evaluation framework, task categories, metrics
- [Sprints](docs/sprints/README.md) — Detailed sprint breakdowns

## Supported Formats

- **Jupyter Notebooks** (`.ipynb`) — Full support
- **Google Colab** (`.ipynb`) — Full support
- **Marimo** (`.py`) — Read-only support

## License

Apache-2.0

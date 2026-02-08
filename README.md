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

## For Coding Agents

### Agent Skill

The agent skill teaches agents notebook best practices:

```bash
# For Claude Code
cp skills/notebook/SKILL.md .claude/skills/notebook/SKILL.md

# For Cursor
cp skills/notebook/SKILL.md .cursor/skills/notebook.md
```

### Agent Workflow

1. **Start**: `dasa context` — read project state
2. **Before data code**: `dasa profile --var df` — see exact columns
3. **Before editing cells**: `dasa check` — understand dependencies
4. **Debug errors**: `dasa run --cell N` — rich error context
5. **End of session**: `dasa context --log "..."` — record progress

## Documentation

- [Design](docs/DESIGN.md) — Vision, problem, solution, multi-agent architecture
- [Architecture](docs/ARCHITECTURE.md) — Technical components, session system, package structure
- [Plan](docs/PLAN.md) — Sprint roadmap (6 sprints, MVP = Sprints 0-3)
- [Evaluation](docs/EVAL.md) — Evaluation framework, task categories, metrics
- [Sprints](docs/sprints/README.md) — Detailed sprint breakdowns

## Supported Formats

- **Jupyter Notebooks** (`.ipynb`) — Full support
- **Google Colab** (`.ipynb`) — Full support
- **Marimo** (`.py`) — Planned (Sprint 5)

## License

Apache-2.0

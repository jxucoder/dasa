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

## Workflows

### Starting a Session
1. Run `dasa context` to get project state
2. If no context exists, set goal: `dasa context --set-goal "your goal"`

### Adding Code That Uses Data
1. Run `dasa profile notebook.ipynb --var df` to see columns, types, stats
2. Note exact column names and data issues
3. Write code using the correct column names
4. Run `dasa run notebook.ipynb --cell N` and verify

### Debugging Errors
1. Run `dasa run notebook.ipynb --cell N` to get rich error context
2. Read the available columns/variables and suggestions
3. If data issue, profile the variable: `dasa profile notebook.ipynb --var df`
4. Fix the code and re-run

### Before Modifying Cells
1. Run `dasa check notebook.ipynb` to see state and dependencies
2. Use `dasa check notebook.ipynb --cell N` to see impact of changing cell N
3. Make changes
4. Run affected downstream cells

### End of Session
1. Log what you did: `dasa context --log "description of what was done"`
2. Update status: `dasa context --set-status "current status"`

## Commands Reference

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `dasa profile notebook.ipynb --var df` | See data structure | Before writing data code |
| `dasa check notebook.ipynb` | See notebook health | Before modifying cells |
| `dasa run notebook.ipynb --cell N` | Execute with context | Testing changes |
| `dasa context` | Read project memory | Start of session |
| `dasa context --set-goal "..."` | Set project goal | Start of project |
| `dasa context --log "..."` | Log decision | After key decisions |

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
| **Stale outputs** | Agent works with outdated results |

**Regular coding agents can read and write files. They can't diagnose notebook state.**

## The Solution

DASA provides a **diagnostic CLI** - tools that answer the questions agents need answered:

```bash
# Is this notebook's output trustworthy?
dasa validate notebook.ipynb

# What does this DataFrame actually contain?
dasa profile notebook.ipynb --var df

# If I change cell 3, what else needs to run?
dasa deps notebook.ipynb

# Run this cell (with async support for long operations)
dasa run notebook.ipynb --cell 4 --async

# Will this notebook reproduce from scratch?
dasa replay notebook.ipynb
```

## Quick Start

```bash
# Install
pip install dasa

# Validate notebook state
dasa validate my_analysis.ipynb

# Profile a DataFrame
dasa profile my_analysis.ipynb --var df

# Check dependencies
dasa deps my_analysis.ipynb
```

## Tool Categories

```
┌─────────────────────────────────────────────────────────────┐
│                         DASA Tools                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Understanding        Execution          Manipulation       │
│  ─────────────        ─────────          ────────────       │
│  profile              run                add                │
│  validate             replay             edit               │
│  deps                 status             delete             │
│                                          move               │
│                                                             │
│  State                Info                                  │
│  ─────                ────                                  │
│  vars                 info                                  │
│  kernel               cells                                 │
│  stale                outputs                               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## For Coding Agents

### Claude Code

DASA includes a `CLAUDE.md` file that teaches Claude Code how to use the toolkit. When Claude Code sees this file in your project, it will automatically use DASA commands when working with notebooks.

```bash
# Install DASA in your project
pip install dasa

# The CLAUDE.md file is included - Claude Code will find it automatically
```

### Other Agents (Cursor, Codex, etc.)

Any agent that can run bash commands can use DASA. The commands are self-documenting:

```bash
dasa --help           # List all commands
dasa profile --help   # Help for specific command
```

### Agent Workflow

When an agent works with a notebook, it should:

1. **Validate first**: `dasa validate notebook.ipynb`
2. **Profile data**: `dasa profile notebook.ipynb --var df`
3. **Check dependencies**: `dasa deps notebook.ipynb`
4. **Execute with context**: `dasa run notebook.ipynb --cell N`
5. **Verify reproducibility**: `dasa replay notebook.ipynb`

## Example Workflow

```bash
# 1. Agent receives task: "Add a visualization of sales by region"

# 2. First, understand the data
$ dasa profile notebook.ipynb --var sales_data

DataFrame: sales_data (10000 rows × 5 columns)
Columns:
  region      object     4 unique: ['North', 'South', 'East', 'West']
  sales       float64    min=100, max=50000, mean=5200
  date        datetime64 2023-01-01 to 2024-12-31
  ...

# 3. Check what cells exist and their dependencies
$ dasa deps notebook.ipynb

Cell 1 (load_data) → Cell 2, Cell 3
Cell 2 (transform) → Cell 3
Cell 3 (current visualizations) [TERMINAL]

# 4. Add the new visualization cell
$ dasa add notebook.ipynb --after 3 --code "
import matplotlib.pyplot as plt
sales_by_region = sales_data.groupby('region')['sales'].sum()
plt.bar(sales_by_region.index, sales_by_region.values)
plt.title('Sales by Region')
plt.show()
"

# 5. Run and verify
$ dasa run notebook.ipynb --cell 4

Cell 4 executed successfully (0.23s)
Output: matplotlib.Figure (bar chart with 4 bars)
```

## Documentation

- [Problems We Solve](docs/PROBLEMS.md) - Deep dive into notebook issues
- [CLI Reference](docs/CLI.md) - Complete command documentation
- [Integration Guide](docs/INTEGRATION.md) - Working with coding agents
- [Architecture](docs/ARCHITECTURE.md) - Technical design
- [Implementation Plan](docs/PLAN.md) - Phased development roadmap
- [Evaluation Framework](docs/EVAL.md) - How we measure effectiveness
- [Sprints](docs/sprints/README.md) - Detailed sprint breakdowns

## Supported Formats

- **Jupyter Notebooks** (`.ipynb`) - Full support
- **Google Colab** (`.ipynb`) - Full support
- **Marimo** (`.py`) - Supported

## Philosophy

DASA is built on these principles:

1. **Diagnostic, not operational** - We help agents understand notebooks, not just edit them
2. **Problem-driven** - Every command solves a real data science problem
3. **LLM-friendly output** - All output is structured for AI consumption
4. **Universal** - Works with any agent that can run bash commands

## License

Apache-2.0

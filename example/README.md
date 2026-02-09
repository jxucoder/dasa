# DASA Example Workspace

A hands-on workspace to try all four DASA commands.

## Setup

```bash
# From the repo root, install dasa
uv pip install -e ".[dev]"

# Then cd into this directory
cd example
```

## What's Here

```
example/
├── analysis.ipynb     # Sample notebook (with intentional bugs)
├── data/
│   └── sales.csv      # 500-row sales dataset
└── README.md
```

The notebook has **two intentional bugs** to demonstrate DASA's error handling:
- **Cell 4**: `KeyError` — uses `revenue_usd` instead of `revenue`
- **Cell 8**: `NameError` — references undefined variable `results`

## Try It Out

### 1. Check notebook health

```bash
dasa check analysis.ipynb
```

See state issues, dependency graph, and which cells are stale.

### 2. Profile the data

```bash
# Run cells 1-2 first to load the data
dasa run analysis.ipynb --cell 1
dasa run analysis.ipynb --cell 2

# Now profile the DataFrame
dasa profile analysis.ipynb --var df
```

See columns, types, stats, null rates, and data quality issues.

### 3. Hit the bugs (and see rich error context)

```bash
# This will fail with a KeyError — note the "did you mean?" suggestion
dasa run analysis.ipynb --cell 4

# This will fail with a NameError — note the available variables list
dasa run analysis.ipynb --cell 8
```

### 4. Run the good cells

```bash
# Run the cleaning and aggregation
dasa run analysis.ipynb --cell 3
dasa run analysis.ipynb --cell 5
dasa run analysis.ipynb --cell 9
```

### 5. Set up project context

```bash
# Set a goal
dasa context --set-goal "Analyze regional sales performance, find top category"

# Log progress
dasa context --log "Loaded 500 rows, 5% null revenue, 2% negative values"

# Read it back
dasa context
```

Check the `.dasa/` directory that gets created — it auto-accumulates profiles, state, and logs.

### 6. Check what changed

```bash
# After running some cells, check again
dasa check analysis.ipynb

# See impact of modifying a specific cell
dasa check analysis.ipynb --cell 2
```

## Full Walkthrough

This simulates a real agent workflow:

```bash
# 1. Start: read project state
dasa context

# 2. Assess notebook health
dasa check analysis.ipynb

# 3. Run the imports and data loading
dasa run analysis.ipynb --from 1 --to 2

# 4. Profile the data to see what we're working with
dasa profile analysis.ipynb --var df

# 5. Try running the buggy cell — see the helpful error
dasa run analysis.ipynb --cell 4
#    → KeyError: 'revenue_usd', did you mean 'revenue'?

# 6. Fix the bug in the notebook (change revenue_usd → revenue), then re-run
dasa run analysis.ipynb --cell 4

# 7. Run the analysis cells
dasa run analysis.ipynb --cell 3
dasa run analysis.ipynb --cell 5

# 8. Log what we did
dasa context --log "Fixed revenue column bug, ran sales-by-region analysis"
dasa context --set-status "basic analysis complete, visualization next"

# 9. Check final state
dasa context
```

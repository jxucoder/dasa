# Notebook Agent Skill

This skill teaches you how to work effectively with Jupyter notebooks using DASA tools.

## When This Skill Applies

- Working with `.ipynb` files
- Data science or machine learning tasks
- Tasks involving pandas DataFrames, numpy arrays, or visualizations

## Core Principles

1. **Profile before coding** - Always understand your data before writing code that uses it
2. **Validate state** - Check notebook consistency when things seem wrong
3. **Check dependencies** - Understand impact before modifying cells
4. **Verify reproducibility** - Ensure notebooks work from scratch

## Available Tools

### Understanding Tools

```bash
# Profile a variable to understand its structure
dasa profile notebook.ipynb --var df

# Check notebook state for issues
dasa validate notebook.ipynb

# See cell dependencies
dasa deps notebook.ipynb
dasa deps notebook.ipynb --cell 3  # Impact of changing cell 3
```

### Execution Tools

```bash
# Run a specific cell
dasa run notebook.ipynb --cell 3

# Verify reproducibility
dasa replay notebook.ipynb
```

## Workflows

### Adding Code That Uses Data

1. First, profile the data:
   ```bash
   dasa profile notebook.ipynb --var df
   ```
2. Note the exact column names, types, and any data quality issues
3. Write code using the correct column names
4. Run and verify

### Debugging Errors

1. Run the failing cell to see the error:
   ```bash
   dasa run notebook.ipynb --cell 5
   ```
2. Check the error context and suggestions
3. If it's a data issue, profile the relevant variable
4. Fix and re-run

### Fixing Inconsistent State

1. Validate the notebook:
   ```bash
   dasa validate notebook.ipynb
   ```
2. Review the issues (stale outputs, undefined variables, etc.)
3. Either fix individual cells or replay from scratch:
   ```bash
   dasa replay notebook.ipynb
   ```

### Modifying Cells

1. Check what depends on the cell:
   ```bash
   dasa deps notebook.ipynb --cell 2
   ```
2. Make your changes
3. Re-run affected cells

## Common Mistakes to Avoid

- **Don't assume column names** - Always profile first
- **Don't ignore state warnings** - They indicate real problems
- **Don't modify cells without checking deps** - You'll break downstream cells
- **Don't trust stale outputs** - Re-run to verify

# DASA Examples

This directory contains example notebooks and usage demonstrations.

## Sample Notebook

`sample_analysis.ipynb` - A typical data analysis notebook with:
- Data loading and creation
- Groupby operations
- Summary statistics

## Example Commands

### 1. Understand the notebook

```bash
$ dasa info sample_analysis.ipynb

Notebook: sample_analysis.ipynb
  Path: /path/to/sample_analysis.ipynb
  Format: Jupyter (nbformat 4)
  Kernel: python3
  Cells: 6 (5 code, 1 markdown)
  Packages imported: np, pd

$ dasa cells sample_analysis.ipynb

Cells in notebook (6 total)
[0] markdown - # Sample Data Analysis
[1] code (2 lines) - defines: np, pd
[2] code (8 lines) - defines: df, data
[3] code (4 lines) - defines: sales_by_region
[4] code (3 lines) - defines: avg_units, top_region
[5] code (6 lines) - defines: total_sales
```

### 2. Validate notebook state

```bash
$ dasa validate sample_analysis.ipynb

Notebook State Analysis
OK Notebook state is consistent

Execution Order:
  Actual: [1] -> [2] -> [3] -> [4] -> [5]
```

### 3. Check cell dependencies

```bash
$ dasa deps sample_analysis.ipynb

Dependency Graph

Cell 1 (import pandas as pd) - defines: np, pd
  --> Cell 2

Cell 2 (# Create sample sales data) - defines: data, df
  --> Cell 3, Cell 4, Cell 5

Cell 3 (# Analyze sales by region) - defines: sales_by_region [TERMINAL]

Cell 4 (# Calculate average units per region) - defines: avg_units, top_region
  --> Cell 5

Cell 5 (# Summary statistics) - defines: total_sales [TERMINAL]
```

### 4. List variables

```bash
$ dasa vars sample_analysis.ipynb

Variables in notebook:
  Cell 1: np, pd
  Cell 2: data, df
  Cell 3: sales_by_region
  Cell 4: avg_units, top_region
  Cell 5: total_sales
```

### 5. View cell outputs

```bash
$ dasa outputs sample_analysis.ipynb

Cell outputs:
[3] Sales by Region:
    region
    East     137842.45
    North    148293.12
    ...

[5] Summary Statistics:
    Total Sales: $560,160.24
    Top Region: North
    Average Units: 54.3
```

### 6. Run a specific cell

```bash
$ dasa run sample_analysis.ipynb --cell 3

Executing cell 3...
Output:
Sales by Region:
region
East     137842.45
North    148293.12
...
```

### 7. Run stale cells

```bash
# After modifying cell 2, see what's stale
$ dasa stale sample_analysis.ipynb

Stale cells: 3, 4, 5
  Cell 3 depends on: df (modified in cell 2)
  Cell 4 depends on: df (modified in cell 2)
  Cell 5 depends on: sales_by_region, top_region

# Re-run all stale cells
$ dasa run sample_analysis.ipynb --stale

Running 3 stale cells...
✓ Cell 3 (0.12s)
✓ Cell 4 (0.08s)
✓ Cell 5 (0.05s)
```

### 8. Add a new cell

```bash
$ dasa add sample_analysis.ipynb "print(df.describe())" --after 2

Added cell 3: print(df.describe())
```

### 9. Edit an existing cell

```bash
$ dasa edit sample_analysis.ipynb --cell 5 "
# Updated summary
print(f'Total Revenue: \${total_sales:,.2f}')
print(f'Best Region: {top_region}')
"

Updated cell 5
```

### 10. Long-running execution (async)

```bash
# Start a long computation in background
$ dasa run sample_analysis.ipynb --cell 10 --async

Started job nb_abc123
Use 'dasa status nb_abc123' to check progress

# Check status
$ dasa status

JOBS
ID          STATUS    PROGRESS  NOTEBOOK
nb_abc123   running   60%       sample_analysis.ipynb

# Get results when done
$ dasa result nb_abc123

Results for job nb_abc123:
✓ Cell 10 completed (45.2s)
Output: Model trained with 95.2% accuracy
```

## JSON Output

All commands support `--format json` for programmatic use:

```bash
$ dasa profile sample_analysis.ipynb --format json

{
  "notebook": "sample_analysis.ipynb",
  "cells": {
    "total": 6,
    "code": 5,
    "markdown": 1
  },
  "imports": ["pandas", "numpy"],
  "variables": ["pd", "np", "data", "df", "sales_by_region", "avg_units", "top_region", "total_sales"]
}
```

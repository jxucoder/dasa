# Problems DASA Solves

This document explains the unique challenges of data science notebooks and how DASA addresses them.

## The Notebook Problem

> "36% of Jupyter notebooks on GitHub aren't reproducible"
> — [Study of 10 million Jupyter notebooks](https://blog.jetbrains.com/datalore/2020/12/17/we-downloaded-10-000-000-jupyter-notebooks-from-github-this-is-what-we-learned/)

Notebooks are the dominant tool for data science, but they have fundamental issues that make them difficult for both humans and AI agents to work with reliably.

---

## Problem 1: Hidden State

### The Issue

In Jupyter, you can:
- Run cells out of order
- Delete a cell but keep its variables in memory
- Modify a cell but not re-run dependent cells

This creates "hidden state" - the code you see doesn't match the actual program state.

### Example

```python
# Cell 1: Run this first
x = 10

# Cell 2: Run this second
y = x + 5  # y = 15

# Cell 3: Now delete Cell 1 and run this
print(y)  # Still prints 15! But x doesn't exist anymore
```

### Impact on Agents

An agent looking at a notebook can't trust that:
- The outputs shown are current
- The variables exist
- Running the notebook fresh would produce the same results

### DASA Solution

```bash
$ dasa validate notebook.ipynb

⚠ INCONSISTENT STATE DETECTED

Issues:
  - Cell 3 uses variable 'x' which no longer exists (Cell 1 deleted)
  - Cell 5 output is STALE (code modified after last execution)
  
Recommendation: Run `dasa replay notebook.ipynb` to reset
```

---

## Problem 2: Unknown Data

### The Issue

In software engineering, you know your types and interfaces. In data science, you're exploring unknown data:
- What columns does this CSV have?
- What are the data types?
- Are there nulls? Outliers?
- What's the distribution?

### Impact on Agents

An agent asked to "plot revenue by region" doesn't know:
- Is the column named `revenue` or `revenue_usd` or `sales`?
- Is `region` a string or a category?
- Are there null values to handle?

Without this context, the agent writes code that fails.

### DASA Solution

```bash
$ dasa profile notebook.ipynb --var df

DataFrame: df (50000 rows × 12 columns)

Columns:
  user_id     int64      50000 unique, no nulls
  revenue     float64    min=-500, max=99847, mean=1523
                         ⚠ 2341 nulls (4.7%)
                         ⚠ 23 negative values
  region      object     4 unique: ['North', 'South', 'East', 'West']
  signup      datetime64 2020-01-01 to 2024-12-31

Data Quality Issues:
  ⚠ revenue: 4.7% null, has negative values (likely errors)
```

Now the agent knows exactly what it's working with.

---

## Problem 3: Cell Dependencies

### The Issue

Notebooks have implicit dependencies between cells:
- Cell 3 uses `df` defined in Cell 1
- Cell 5 uses `model` trained in Cell 4
- Changing Cell 1 invalidates Cells 3, 4, and 5

These dependencies aren't visible in the notebook interface.

### Impact on Agents

An agent modifying Cell 2 doesn't know:
- Which other cells will break?
- What needs to be re-run?
- What's the correct execution order?

### DASA Solution

```bash
$ dasa deps notebook.ipynb

Dependency Graph:

Cell 0 (imports)
  └─→ Cell 1, Cell 2, Cell 3, Cell 4, Cell 5

Cell 1 (load_data) - defines: df
  └─→ Cell 2, Cell 3, Cell 4

Cell 2 (transform) - defines: clean_df
  └─→ Cell 3, Cell 4

Cell 4 (train) - defines: model
  └─→ Cell 5

If you modify Cell 1:
  → Cells 2, 3, 4, 5 need re-run (4 cells affected)
```

---

## Problem 4: Long-Running Execution

### The Issue

Data science operations can take a long time:
- Loading large datasets: minutes
- Training models: hours
- Processing big data: hours to days

### Impact on Agents

An agent running `dasa run notebook.ipynb --cell 4` might wait forever for model training to complete, or timeout and lose progress.

### DASA Solution

```bash
# Start long operation in background
$ dasa run notebook.ipynb --cell 4 --async

Started async job: abc123
Estimated duration: ~2 hours (based on history)

# Check progress
$ dasa status abc123

Job abc123: RUNNING
Progress: Epoch 45/100 (45%)
Runtime: 54 minutes

Output:
  Epoch 43: loss=0.234, acc=0.91
  Epoch 44: loss=0.231, acc=0.91
  Epoch 45: loss=0.228, acc=0.92 (current)

# Cancel if needed
$ dasa cancel abc123
```

---

## Problem 5: Rich Outputs

### The Issue

Data science produces rich outputs:
- Plots and visualizations
- Interactive tables
- HTML reports
- Images

These aren't captured by simple text output.

### Impact on Agents

An agent running a cell that produces a plot only sees:
```
<Figure size 640x480 with 1 Axes>
```

This tells it nothing about what the plot shows.

### DASA Solution

```bash
$ dasa run notebook.ipynb --cell 3

Cell 3 executed (0.42s)

Output Type: matplotlib.Figure
Description: Bar chart showing 4 bars for regions (North, South, East, West)
             North has highest value (~15000), West lowest (~8000)
             Title: "Sales by Region"
             
Saved to: .dasa/outputs/cell_3.png
```

---

## Problem 6: Reproducibility

### The Issue

A notebook that "works" might not reproduce because:
- Random seeds not set
- Files not tracked
- Package versions differ
- Environment variables missing

### Impact on Agents

An agent can't verify if a notebook will work:
- On another machine
- After restarting the kernel
- When shared with colleagues

### DASA Solution

```bash
$ dasa replay notebook.ipynb

Replaying notebook from scratch (new kernel)...

Cell 0: ✓ imports successful
Cell 1: ✓ data loaded
Cell 2: ✓ transform complete
Cell 3: ⚠ OUTPUT DIFFERS
        Reason: Random seed not set
        Original: accuracy=0.923
        Replay: accuracy=0.919
Cell 4: ✓ model trained
Cell 5: ✗ FAILED
        Error: FileNotFoundError: 'config/settings.yaml'
        This file exists locally but wasn't tracked

Reproducibility Score: 66% (4/6 cells)

Issues Found:
  1. Random state not set in Cell 3 - add np.random.seed(42)
  2. Missing file: config/settings.yaml - commit to repo
```

---

## Problem 7: Out-of-Order Execution

### The Issue

Users (and agents) can run cells in any order:
- Run Cell 5 before Cell 2
- Skip Cell 3 entirely
- Run Cell 1 twice

This creates nonsensical state.

### Impact on Agents

An agent doesn't know:
- What order cells were actually run
- Whether the current state makes sense
- What the "correct" order should be

### DASA Solution

```bash
$ dasa validate notebook.ipynb

Execution History:
  [4] → [2] → [5] → [3]  ⚠ Out of order!

Correct Order (based on dependencies):
  [0] → [1] → [2] → [3] → [4] → [5]

Issues:
  - Cell 5 ran before Cell 4 (needs model from Cell 4)
  - Cell 3 ran last but should run before Cell 4
```

---

## Summary

| Problem | Traditional Notebooks | With DASA |
|---------|----------------------|-----------|
| Hidden state | Invisible, causes bugs | `validate` detects |
| Unknown data | Must run code to see | `profile` shows all |
| Dependencies | Must trace manually | `deps` shows graph |
| Long execution | Blocks indefinitely | `run --async` backgrounds |
| Rich outputs | Just shows type | Describes content |
| Reproducibility | Hope and pray | `replay` verifies |
| Out-of-order | User's problem | `validate` detects |

**DASA makes notebook problems visible and actionable.**

# DASA CLI Reference

Complete reference for all DASA command-line tools.

## Installation

```bash
pip install dasa
```

---

## Understanding Tools

### `dasa profile`

Deep data profiling for variables in the notebook.

```bash
dasa profile <notebook> --var <variable_name>
```

**Options:**
- `--var, -v` - Variable name to profile (required)
- `--sample, -s` - Number of sample rows to show (default: 5)
- `--full` - Show full statistics for all columns

**Example:**
```bash
$ dasa profile analysis.ipynb --var df

DataFrame: df (50000 rows × 12 columns)
Memory: 4.6 MB

Columns:
  user_id     int64      50000 unique, no nulls
  email       object     49823 unique, 177 nulls (0.4%)
  revenue     float64    min=-500, max=99847, mean=1523
                         ⚠ 2341 nulls (4.7%)
                         ⚠ 23 negative values
  signup      datetime64 2020-01-01 to 2024-12-31
  category    category   5 unique: ['A', 'B', 'C', 'D', 'E']

Data Quality Issues:
  ⚠ revenue: 4.7% null, has negative values
  ⚠ email: 177 nulls

Sample (first 3 rows):
  user_id | email              | revenue | signup     | category
  1       | user1@example.com  | 5000.0  | 2024-01-01 | A
  2       | user2@example.com  | 3200.0  | 2024-01-02 | B
  3       | NULL               | -500.0  | 2024-01-03 | A  ⚠
```

---

### `dasa validate`

Check notebook state for consistency issues.

```bash
dasa validate <notebook>
```

**Options:**
- `--strict` - Fail on any warning (for CI/CD)

**Example:**
```bash
$ dasa validate analysis.ipynb

Notebook State Analysis:

⚠ INCONSISTENT STATE DETECTED

Issues:
  - Cell 3: Output is STALE (code modified after last run)
  - Cell 5: Uses variable 'df' but Cell 2 (defines 'df') hasn't run
  - Cell 7: Uses deleted variable 'model'

Execution History:
  [4] → [2] → [5] → [3] (out of order!)

Correct Order:
  [0] → [1] → [2] → [3] → [4] → [5]

Recommendation: Run `dasa replay analysis.ipynb` to reset state
```

---

### `dasa deps`

Analyze cell dependencies.

```bash
dasa deps <notebook>
```

**Options:**
- `--cell, -c` - Show impact of modifying specific cell
- `--format` - Output format: `tree` (default), `json`, `dot`

**Example:**
```bash
$ dasa deps analysis.ipynb

Dependency Graph:

Cell 0 (imports) - defines: pd, np, plt
  └─→ Cell 1, Cell 2, Cell 3, Cell 4, Cell 5

Cell 1 (load_data) - defines: df, raw_data
  └─→ Cell 2, Cell 4

Cell 2 (transform) - defines: clean_df
  └─→ Cell 3

Cell 3 (visualize) [TERMINAL]

Cell 4 (train_model) - defines: model, X_train, y_train
  └─→ Cell 5

Cell 5 (evaluate) [TERMINAL]

$ dasa deps analysis.ipynb --cell 1

If you modify Cell 1:
  → Cell 2 needs re-run (uses: df)
  → Cell 3 needs re-run (uses: clean_df from Cell 2)
  → Cell 4 needs re-run (uses: df)
  → Cell 5 needs re-run (uses: model from Cell 4)
  
Total: 4 cells affected
```

---

## Execution Tools

### `dasa run`

Execute notebook cells.

```bash
dasa run <notebook> [options]
```

**Options:**
- `--cell, -c` - Run specific cell (by index)
- `--from` - Run from cell N to end
- `--to` - Run from start to cell N
- `--stale` - Run all stale cells
- `--all` - Run all cells
- `--async` - Run in background (for long operations)
- `--timeout` - Timeout in seconds (default: 300)

**Examples:**
```bash
# Run single cell
$ dasa run analysis.ipynb --cell 3

Cell 3 executed successfully (0.23s)

stdout:
  Processing 50000 rows...
  Done.

Output: DataFrame (1000 rows × 5 columns)

# Run with error
$ dasa run analysis.ipynb --cell 5

Cell 5 FAILED (0.02s)

Error: KeyError: 'revenue_usd'

Context:
  Line 3: df['profit'] = df['revenue_usd'] - df['cost']
  
Available columns in df:
  - revenue (not revenue_usd) ← Did you mean this?
  - cost
  - user_id

Suggestion: Column 'revenue_usd' doesn't exist. Try 'revenue'.

# Async execution for long operations
$ dasa run analysis.ipynb --cell 4 --async

Started async job: abc123
Estimated duration: ~15 minutes (based on history)

Use `dasa status abc123` to check progress
Use `dasa cancel abc123` to stop
Use `dasa wait abc123` to block until complete
```

---

### `dasa status`

Check status of async job.

```bash
dasa status <job_id>
```

**Example:**
```bash
$ dasa status abc123

Job abc123: RUNNING
Cell: 4 (train_model)
Started: 5 minutes ago
Progress: Epoch 3/10 (30%)

Recent output:
  Epoch 1: loss=0.542, acc=0.78
  Epoch 2: loss=0.423, acc=0.84
  Epoch 3: loss=0.387, acc=0.86 (in progress)
```

---

### `dasa cancel`

Cancel an async job.

```bash
dasa cancel <job_id>
```

---

### `dasa replay`

Run notebook from scratch and verify reproducibility.

```bash
dasa replay <notebook>
```

**Options:**
- `--compare` - Compare outputs with existing (default: true)
- `--save` - Save replayed notebook to file
- `--strict` - Fail on any difference

**Example:**
```bash
$ dasa replay analysis.ipynb

Replaying notebook from scratch (new kernel)...

Cell 0: ✓ imports (0.5s)
Cell 1: ✓ load_data (2.3s) - outputs match
Cell 2: ✓ transform (0.8s) - outputs match
Cell 3: ⚠ visualize (0.4s) - OUTPUT DIFFERS
        Reason: Random seed not set
        Diff: Values in bar chart differ by ~2%
Cell 4: ✓ train_model (45.2s) - outputs match
Cell 5: ✗ evaluate - FAILED
        Error: FileNotFoundError: 'data/test.csv'
        This file exists locally but wasn't committed

Total time: 49.2s
Reproducibility Score: 66% (4/6 cells)

Issues Found:
  1. Cell 3: Set random seed with np.random.seed(42)
  2. Cell 5: Commit data/test.csv to repository
```

---

## Manipulation Tools

### `dasa add`

Add a new cell to the notebook.

```bash
dasa add <notebook> --code <code> [options]
```

**Options:**
- `--code` - Python code for the cell
- `--markdown` - Markdown content (mutually exclusive with --code)
- `--at` - Insert at specific index
- `--after` - Insert after specific cell
- `--before` - Insert before specific cell

**Examples:**
```bash
# Add code cell after cell 3
$ dasa add analysis.ipynb --after 3 --code "plt.bar(df['region'], df['sales'])"

Added Cell 4 (code)
Notebook saved.

# Add markdown cell at the beginning
$ dasa add analysis.ipynb --at 0 --markdown "# Sales Analysis Report"

Added Cell 0 (markdown)
Notebook saved.
```

---

### `dasa edit`

Edit an existing cell.

```bash
dasa edit <notebook> --cell <index> --code <new_code>
```

**Example:**
```bash
$ dasa edit analysis.ipynb --cell 3 --code "plt.bar(df['region'], df['revenue'])"

Cell 3 updated.
Previous: plt.bar(df['region'], df['sales'])
New: plt.bar(df['region'], df['revenue'])

⚠ This cell has downstream dependents: Cell 4, Cell 5
Run `dasa run analysis.ipynb --from 3` to update all.
```

---

### `dasa delete`

Delete a cell.

```bash
dasa delete <notebook> --cell <index>
```

**Options:**
- `--force` - Skip confirmation

**Example:**
```bash
$ dasa delete analysis.ipynb --cell 5

⚠ Cell 5 defines variables used elsewhere:
  - model (used in Cell 6)

Delete anyway? [y/N] y

Cell 5 deleted.
⚠ Cell 6 now references undefined variable 'model'
```

---

### `dasa move`

Move a cell to a different position.

```bash
dasa move <notebook> --cell <index> --to <new_index>
```

---

## State Tools

### `dasa vars`

List variables in kernel memory.

```bash
dasa vars <notebook>
```

**Options:**
- `--type` - Filter by type (DataFrame, ndarray, etc.)
- `--sort` - Sort by: name, size, cell (default: cell)

**Example:**
```bash
$ dasa vars analysis.ipynb

Variables in kernel memory:

Name          Type              Size      Defined    Used In
────────────────────────────────────────────────────────────
df            DataFrame         4.6 MB    Cell 1     Cell 2,3,4
clean_df      DataFrame         3.2 MB    Cell 2     Cell 3
model         RandomForest      156 MB    Cell 4     Cell 5
X_train       ndarray           890 MB    Cell 2     Cell 4
y_train       ndarray           400 KB    Cell 2     Cell 4
predictions   ndarray           12 KB     Cell 5     -

Total: 6 variables, 1.05 GB
```

---

### `dasa kernel`

Manage the notebook kernel.

```bash
dasa kernel <notebook> <action>
```

**Actions:**
- `status` - Show kernel status
- `restart` - Restart kernel (clears all state)
- `interrupt` - Interrupt current execution

**Examples:**
```bash
$ dasa kernel analysis.ipynb status

Kernel Status:
  Type: python3
  State: IDLE
  PID: 12345
  Memory: 2.1 GB
  Uptime: 45 minutes
  
Variables in memory: 23 (1.05 GB total)

$ dasa kernel analysis.ipynb restart

Kernel restarted.
All 23 variables cleared (freed 1.05 GB).
Notebook ready for fresh execution.
```

---

### `dasa stale`

Find cells with outdated outputs.

```bash
dasa stale <notebook>
```

**Example:**
```bash
$ dasa stale analysis.ipynb

Cell 2 was modified since last run.

Stale cells (need re-run):
  ⚠ Cell 2 (modified directly)
  ⚠ Cell 3 (depends on Cell 2 via: clean_df)
  ⚠ Cell 5 (depends on Cell 2 via: df → model)

Up to date:
  ✓ Cell 0, Cell 1, Cell 4

Run `dasa run analysis.ipynb --stale` to update all stale cells.
```

---

## Info Tools

### `dasa info`

Show notebook metadata.

```bash
dasa info <notebook>
```

**Example:**
```bash
$ dasa info analysis.ipynb

Notebook: analysis.ipynb
Format: Jupyter (nbformat 4.5)
Kernel: python3
Cells: 6 (5 code, 1 markdown)

Created: 2024-01-15 10:30:00
Modified: 2024-01-20 14:22:00
Size: 125 KB

Packages imported:
  pandas, numpy, matplotlib, sklearn
```

---

### `dasa cells`

List all cells in the notebook.

```bash
dasa cells <notebook>
```

**Options:**
- `--type` - Filter by type (code, markdown)
- `--full` - Show full cell content

**Example:**
```bash
$ dasa cells analysis.ipynb

Notebook: analysis.ipynb (6 cells)

[0] markdown
    # Sales Analysis

[1] code (5 lines) - defines: df, raw_data
    import pandas as pd
    df = pd.read_csv('sales.csv')
    ...

[2] code (8 lines) - defines: clean_df
    clean_df = df.dropna()
    clean_df['revenue'] = clean_df['revenue'].clip(lower=0)
    ...

[3] code (4 lines) [STALE]
    plt.figure(figsize=(10, 6))
    plt.bar(clean_df['region'], clean_df['revenue'])
    ...

[4] code (12 lines) - defines: model, X_train, y_train
    from sklearn.ensemble import RandomForestRegressor
    ...

[5] code (3 lines) - defines: predictions
    predictions = model.predict(X_test)
    ...
```

---

### `dasa outputs`

View cell outputs.

```bash
dasa outputs <notebook> [--cell <index>]
```

**Example:**
```bash
$ dasa outputs analysis.ipynb --cell 3

Cell 3 Output:

Type: matplotlib.Figure
Size: 45 KB

Description: Bar chart with 4 bars
  - X-axis: regions (North, South, East, West)
  - Y-axis: revenue (range: 0 to 50000)
  - North has highest bar (~45000)
  - West has lowest bar (~12000)
  - Title: "Revenue by Region"

Saved to: .dasa/outputs/cell_3.png
```

---

## Global Options

These options work with any command:

- `--format` - Output format: `text` (default), `json`
- `--quiet` - Suppress non-essential output
- `--verbose` - Show detailed information
- `--help` - Show help for command

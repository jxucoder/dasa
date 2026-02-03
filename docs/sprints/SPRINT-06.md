# Sprint 6: Info Tools & Async

**Goal:** Implement info commands and async execution infrastructure.

**Duration:** ~3 days

**Prerequisite:** Sprint 5 (Manipulation tools)

---

## Deliverables

| # | Deliverable | Description |
|---|-------------|-------------|
| 1 | `dasa info` | Show notebook metadata |
| 2 | `dasa cells` | List all cells with previews |
| 3 | `dasa outputs` | View cell outputs |
| 4 | Async execution | Background execution with status/cancel |

---

## Tasks

### 6.1 Info Command

```bash
dasa info notebook.ipynb

# Output:
# Notebook: analysis.ipynb
# Format: Jupyter (nbformat 4.5)
# Kernel: python3
# Cells: 6 (5 code, 1 markdown)
#
# Created: 2024-01-15 10:30:00
# Modified: 2024-01-20 14:22:00
# Size: 125 KB
#
# Packages imported:
#   pandas, numpy, matplotlib, sklearn
```

---

### 6.2 Cells Command

```bash
dasa cells notebook.ipynb

# Output:
# [0] markdown
#     # Sales Analysis
#
# [1] code (5 lines) - defines: df, raw_data
#     import pandas as pd
#     df = pd.read_csv('sales.csv')
#     ...
#
# [2] code (8 lines) - defines: clean_df [STALE]
#     clean_df = df.dropna()
#     ...
```

**Features:**
- List all cells with index and type
- Show preview of content
- Show definitions
- Mark stale cells

---

### 6.3 Outputs Command

```bash
dasa outputs notebook.ipynb --cell 3

# Output:
# Cell 3 Output:
#
# Type: matplotlib.Figure
# Size: 45 KB
#
# Description: Bar chart with 4 bars
#   - X-axis: regions (North, South, East, West)
#   - Y-axis: revenue (range: 0 to 50000)
```

**Features:**
- Show output type and size
- Basic description (heuristics, not vision)
- Save to `.dasa/outputs/`

---

### 6.4 Async Execution

```bash
# Start long operation in background
dasa run notebook.ipynb --cell 4 --async
# Output: Started job abc123

# Check progress
dasa status abc123
# Output: RUNNING, Epoch 5/100 (5%)

# Cancel if needed
dasa cancel abc123
```

**Architecture:**
- Jobs stored in `.dasa/jobs/`
- Each job has: PID, status, output log
- Background process via subprocess
- Polling for status updates

---

## Acceptance Criteria

- [ ] `dasa info` shows notebook metadata
- [ ] `dasa cells` lists all cells with previews
- [ ] `dasa outputs` shows output info
- [ ] `dasa run --async` backgrounds execution
- [ ] `dasa status` shows job progress
- [ ] `dasa cancel` terminates job

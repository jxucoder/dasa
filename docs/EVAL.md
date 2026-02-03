# DASA Evaluation Framework

How to measure whether DASA actually helps coding agents work with notebooks.

## Overview

DASA's value proposition is that agents perform better on data science tasks when equipped with diagnostic tools. We need to prove this with measurable benchmarks.

**Core Question:** Do agents complete notebook tasks more successfully with DASA than without?

---

## Evaluation Design

### A/B Test Structure

```
┌─────────────────────────────────────────────────────────────────┐
│                     Evaluation Setup                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Condition A: Baseline (No DASA)                                │
│  ───────────────────────────────                                │
│  • Agent can read/write notebook files                          │
│  • Agent can run bash commands                                  │
│  • Agent has general notebook knowledge                         │
│                                                                 │
│  Condition B: With DASA                                         │
│  ──────────────────────                                         │
│  • Same as Condition A, plus:                                   │
│  • SKILL.md loaded (teaches best practices)                     │
│  • DASA CLI tools available                                     │
│                                                                 │
│  Control Variables                                              │
│  ─────────────────                                              │
│  • Same LLM model                                               │
│  • Same task prompts                                            │
│  • Same test notebooks                                          │
│  • Same max iterations (20)                                     │
│  • Same evaluation criteria                                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Task Categories

### Category 1: Data Understanding

Agent must answer questions about data without prior knowledge.

| Task ID | Prompt | Test Notebook | Success Criteria |
|---------|--------|---------------|------------------|
| DU-01 | "What columns have >10% null values?" | df with nulls | Lists correct columns |
| DU-02 | "What's the range of the 'amount' column?" | numeric data | Correct min/max |
| DU-03 | "How many unique categories are there?" | categorical data | Correct count |
| DU-04 | "Are there any data quality issues?" | messy data | Identifies issues |

**Why DASA helps:** `dasa profile --var df` shows exact column info, nulls, ranges.

### Category 2: Bug Fixing

Agent must fix errors in notebook cells.

| Task ID | Prompt | Test Notebook | Success Criteria |
|---------|--------|---------------|------------------|
| BF-01 | "Fix the KeyError in cell 5" | Wrong column name | Cell executes |
| BF-02 | "Cell 3 is failing, debug it" | NameError | Cell executes |
| BF-03 | "The model training fails, fix it" | Shape mismatch | Cell executes |
| BF-04 | "Fix all errors in this notebook" | Multiple errors | All cells execute |

**Why DASA helps:** `dasa run --cell N` shows error with context and suggestions.

### Category 3: Visualization

Agent must add visualizations using existing data.

| Task ID | Prompt | Test Notebook | Success Criteria |
|---------|--------|---------------|------------------|
| VZ-01 | "Add a bar chart of sales by region" | Sales DataFrame | Chart renders correctly |
| VZ-02 | "Plot the distribution of ages" | User DataFrame | Histogram renders |
| VZ-03 | "Add a time series of daily revenue" | Time data | Line chart renders |
| VZ-04 | "Create a correlation heatmap" | Numeric DataFrame | Heatmap renders |

**Why DASA helps:** `dasa profile` shows exact column names and types before coding.

### Category 4: State Recovery

Agent must fix notebooks with inconsistent state.

| Task ID | Prompt | Test Notebook | Success Criteria |
|---------|--------|---------------|------------------|
| SR-01 | "The notebook gives wrong results, fix it" | Out-of-order execution | Consistent state |
| SR-02 | "Outputs don't match code, help" | Stale outputs | Fresh outputs |
| SR-03 | "Variable 'model' is undefined but was working" | Deleted cell | Working state |
| SR-04 | "Reset this notebook to a clean state" | Messy state | All cells run in order |

**Why DASA helps:** `dasa validate` identifies exact state issues.

### Category 5: Dependency Reasoning

Agent must understand and manage cell dependencies.

| Task ID | Prompt | Test Notebook | Success Criteria |
|---------|--------|---------------|------------------|
| DR-01 | "If I change cell 1, what else needs to run?" | Multi-cell deps | Correct cell list |
| DR-02 | "Modify the data loading to filter for 2024" | Dependent cells | All deps re-run |
| DR-03 | "Can I delete cell 3 safely?" | Has dependents | Correct warning |
| DR-04 | "What's the execution order for this notebook?" | Complex deps | Correct order |

**Why DASA helps:** `dasa deps` shows dependency graph and impact analysis.

### Category 6: Reproducibility

Agent must make notebooks reproducible.

| Task ID | Prompt | Test Notebook | Success Criteria |
|---------|--------|---------------|------------------|
| RP-01 | "Make this notebook reproducible" | No random seed | Passes replay |
| RP-02 | "Will this notebook run on another machine?" | Missing files | Issues identified |
| RP-03 | "Verify this notebook reproduces correctly" | Unknown state | Accurate assessment |
| RP-04 | "Fix reproducibility issues" | Multiple issues | All fixed |

**Why DASA helps:** `dasa replay` tests reproducibility and identifies issues.

---

## Metrics

### Primary Metrics (Task Success)

| Metric | Description | Measurement |
|--------|-------------|-------------|
| **Task Completion Rate** | % of tasks completed successfully | `successes / total_tasks` |
| **First-Attempt Success** | % completed without errors | `no_error_runs / total_tasks` |
| **Error Rate** | Average errors per task | `total_errors / total_tasks` |

### Efficiency Metrics

| Metric | Description | Measurement |
|--------|-------------|-------------|
| **Iterations** | Tool calls + reasoning steps | Count from transcript |
| **Token Usage** | Total tokens consumed | Sum input + output tokens |
| **Time to Complete** | Wall clock time | End - start time |

### Quality Metrics

| Metric | Description | Measurement |
|--------|-------------|-------------|
| **Reproducibility Score** | Does output notebook reproduce? | `dasa replay` pass rate |
| **Code Correctness** | Does added code execute? | Runtime error check |
| **State Consistency** | Is final state valid? | `dasa validate` pass |

### Behavioral Metrics (DASA-specific)

| Metric | Description | Measurement |
|--------|-------------|-------------|
| **Profiled Before Coding** | Used `dasa profile` before data code | Transcript analysis |
| **Validated State** | Used `dasa validate` when debugging | Transcript analysis |
| **Checked Dependencies** | Used `dasa deps` before edits | Transcript analysis |

---

## Test Notebooks

### Notebook Types

| Type | Characteristics | Used For |
|------|-----------------|----------|
| `clean.ipynb` | All cells in order, runs perfectly | Baseline, visualization |
| `messy.ipynb` | Out-of-order execution, stale outputs | State recovery |
| `broken.ipynb` | Has errors in cells | Bug fixing |
| `complex.ipynb` | Many dependencies, large DataFrames | Understanding, deps |
| `unreproducible.ipynb` | Missing seeds, hardcoded paths | Reproducibility |

### Notebook Specifications

**clean.ipynb**
```
Cell 0: Imports (pandas, numpy, matplotlib)
Cell 1: Load data (df = pd.read_csv(...))
Cell 2: Transform (clean_df = df.dropna())
Cell 3: Visualization (plt.bar(...))
Cell 4: Analysis (summary = clean_df.describe())

State: All cells executed in order, outputs current
```

**messy.ipynb**
```
Same cells as clean.ipynb, but:
- Execution order: [0] → [3] → [1] → [4] → [2]
- Cell 2 output is stale (code modified after run)
- Cell 4 uses variable from deleted cell

State: Inconsistent, outputs don't match code
```

**broken.ipynb**
```
Cell 0: Imports
Cell 1: df = pd.read_csv('data.csv')
Cell 2: df['profit'] = df['revenue_usd'] - df['cost']  # KeyError: 'revenue_usd'
Cell 3: model = train_model(X, y)  # NameError: 'X'
Cell 4: print(results)  # NameError: 'results'

State: Multiple errors, some cells never executed
```

---

## Success Thresholds

| Metric | Baseline (expected) | Target (with DASA) | Improvement |
|--------|--------------------|--------------------|-------------|
| Task Completion | ~60% | >85% | +25 pts |
| First-Attempt Success | ~30% | >60% | +30 pts |
| Avg Errors/Task | ~3.0 | <1.0 | -66% |
| Reproducibility | ~40% | >90% | +50 pts |
| Iterations/Task | ~15 | <10 | -33% |

---

## Evaluation Protocol

### Running Evaluations

```bash
# Run full benchmark
python -m dasa.eval.run --output results/

# Run specific category
python -m dasa.eval.run --category data_understanding

# Run with specific model
python -m dasa.eval.run --model claude-3-5-sonnet

# Compare conditions
python -m dasa.eval.analyze results/
```

### Evaluation Flow

```
1. Load task definition
2. Load test notebook
3. Initialize agent with/without DASA
4. Run agent on task (max 20 iterations)
5. Capture transcript (tool calls, errors, output)
6. Check success criteria
7. Run quality checks (validate, replay)
8. Record metrics
9. Repeat for statistical significance (n=3 per task)
```

### Statistical Significance

- Run each task 3+ times per condition
- Report mean ± standard deviation
- Use paired t-test for comparison
- Require p < 0.05 for significance claims

---

## Directory Structure

```
eval/
├── README.md                   # Quick start guide
├── tasks/                      # Task definitions
│   ├── data_understanding/
│   │   ├── DU-01.json
│   │   ├── DU-02.json
│   │   └── ...
│   ├── bug_fixing/
│   ├── visualization/
│   ├── state_recovery/
│   ├── dependency_reasoning/
│   └── reproducibility/
├── notebooks/                  # Test notebooks
│   ├── clean.ipynb
│   ├── messy.ipynb
│   ├── broken.ipynb
│   ├── complex.ipynb
│   └── unreproducible.ipynb
├── data/                       # Test data files
│   └── sales.csv
├── harness/                    # Evaluation code
│   ├── __init__.py
│   ├── runner.py               # Main evaluation loop
│   ├── agent.py                # Agent wrapper
│   ├── checker.py              # Success criteria checks
│   └── metrics.py              # Metric computation
├── results/                    # Output directory
│   └── .gitkeep
└── analyze.py                  # Results analysis
```

### Task Definition Format

```json
{
  "id": "DU-01",
  "category": "data_understanding",
  "name": "Find Null Columns",
  "prompt": "What columns in the DataFrame 'df' have more than 10% null values?",
  "notebook": "complex.ipynb",
  "setup": {
    "ensure_kernel": true,
    "run_cells": [0, 1]
  },
  "success_criteria": {
    "type": "contains_all",
    "expected": ["revenue", "email"],
    "case_sensitive": false
  },
  "difficulty": "easy",
  "tags": ["profiling", "data-quality"]
}
```

---

## Implementation Priority

Evaluation infrastructure is built **first** to enable test-driven development:

1. **Phase 0a:** Create test notebooks (clean, messy, broken)
2. **Phase 0b:** Create task definitions (start with 2 per category)
3. **Phase 0c:** Build evaluation harness (runner, checker, metrics)
4. **Phase 0d:** Establish baseline (run without DASA)
5. **Then:** Build DASA tools, measuring improvement after each

This ensures every feature added shows measurable progress.

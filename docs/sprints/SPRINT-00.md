# Sprint 0: Evaluation Infrastructure

**Goal:** Build evaluation framework before any features to enable test-driven development.

**Duration:** ~2-3 days

---

## Deliverables

| # | Deliverable | Description |
|---|-------------|-------------|
| 1 | Test notebooks | 5 notebooks covering different states |
| 2 | Test data | CSV files used by notebooks |
| 3 | Task definitions | 12-18 JSON task files |
| 4 | Eval harness | Python code to run evaluations |
| 5 | Baseline results | Metrics without DASA |

---

## Tasks

### 0.1 Create Test Data

Create `eval/data/sales.csv` with realistic data for testing:

```csv
# Columns needed:
# - id (int): unique identifier
# - date (datetime): transaction date
# - region (str): North, South, East, West
# - revenue (float): has some nulls, some negatives
# - cost (float): always positive
# - category (str): A, B, C, D, E
# - email (str): has some nulls
```

**Requirements:**
- ~1000 rows
- `revenue`: 5% nulls, 2% negative values
- `email`: 3% nulls
- Dates: 2023-01-01 to 2024-12-31

**File:** `eval/data/sales.csv`

---

### 0.2 Create Test Notebooks

#### 0.2.1 `clean.ipynb` - Perfect State

```python
# Cell 0: Imports
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Cell 1: Load data
df = pd.read_csv('../data/sales.csv')
df['date'] = pd.to_datetime(df['date'])

# Cell 2: Transform
clean_df = df.dropna(subset=['revenue'])
clean_df = clean_df[clean_df['revenue'] >= 0]

# Cell 3: Aggregate
sales_by_region = clean_df.groupby('region')['revenue'].sum()

# Cell 4: Visualize
plt.bar(sales_by_region.index, sales_by_region.values)
plt.title('Sales by Region')
plt.show()

# Cell 5: Summary
summary = clean_df.describe()
print(summary)
```

**State:** All cells executed in order [0,1,2,3,4,5], outputs current.

---

#### 0.2.2 `messy.ipynb` - Inconsistent State

Same code as `clean.ipynb`, but:
- Execution order: [0] → [3] → [1] → [5] → [2] → [4]
- Cell 2 code modified after execution (added a comment)
- Cell 4 output is from different data

**State:** Out-of-order, stale outputs.

---

#### 0.2.3 `broken.ipynb` - Has Errors

```python
# Cell 0: Imports
import pandas as pd
import numpy as np

# Cell 1: Load data
df = pd.read_csv('../data/sales.csv')

# Cell 2: ERROR - wrong column name
df['profit'] = df['revenue_usd'] - df['cost']  # KeyError: 'revenue_usd'

# Cell 3: ERROR - undefined variable
model = train_model(X, y)  # NameError: 'train_model', 'X', 'y'

# Cell 4: ERROR - depends on cell 3
predictions = model.predict(test_data)  # NameError: 'model', 'test_data'

# Cell 5: Works if cell 1 ran
print(df.head())
```

**State:** Cell 0,1 executed. Cells 2,3,4 have errors. Cell 5 never ran.

---

#### 0.2.4 `complex.ipynb` - Many Dependencies

```python
# Cell 0: Imports
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor

# Cell 1: Load data
df = pd.read_csv('../data/sales.csv')
df['date'] = pd.to_datetime(df['date'])

# Cell 2: Feature engineering (depends on cell 1)
df['month'] = df['date'].dt.month
df['day_of_week'] = df['date'].dt.dayofweek
features = df[['month', 'day_of_week', 'cost']].dropna()
target = df.loc[features.index, 'revenue'].fillna(0)

# Cell 3: Split data (depends on cell 2)
X_train, X_test, y_train, y_test = train_test_split(
    features, target, test_size=0.2, random_state=42
)

# Cell 4: Train model (depends on cell 3)
model = RandomForestRegressor(n_estimators=10, random_state=42)
model.fit(X_train, y_train)

# Cell 5: Evaluate (depends on cells 3, 4)
score = model.score(X_test, y_test)
print(f"R² Score: {score:.3f}")

# Cell 6: Feature importance (depends on cells 2, 4)
importance = pd.DataFrame({
    'feature': features.columns,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False)
print(importance)
```

**State:** All cells executed in order.
**Dependencies:** 0→1→2→3→4→5, 0→1→2→4→6

---

#### 0.2.5 `unreproducible.ipynb` - Reproducibility Issues

```python
# Cell 0: Imports (no random seed!)
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Cell 1: Load from hardcoded path
df = pd.read_csv('/Users/someone/data/sales.csv')  # Won't work on other machines

# Cell 2: Random sampling without seed
sample = df.sample(100)  # Different every time

# Cell 3: Uses environment variable
import os
api_key = os.environ['API_KEY']  # Not set on other machines

# Cell 4: Timestamp in output
from datetime import datetime
print(f"Generated at: {datetime.now()}")  # Different every time
```

**State:** All cells executed, but won't reproduce.

---

### 0.3 Create Task Definitions

#### Data Understanding Tasks

**`eval/tasks/data_understanding/DU-01.json`**
```json
{
  "id": "DU-01",
  "category": "data_understanding",
  "name": "Find Null Columns",
  "prompt": "What columns in the DataFrame 'df' have more than 5% null values? List the column names.",
  "notebook": "clean.ipynb",
  "setup": {
    "run_cells": [0, 1]
  },
  "success_criteria": {
    "type": "contains_all",
    "expected": ["revenue", "email"]
  },
  "difficulty": "easy"
}
```

**`eval/tasks/data_understanding/DU-02.json`**
```json
{
  "id": "DU-02",
  "category": "data_understanding",
  "name": "Data Range",
  "prompt": "What is the minimum and maximum value of the 'revenue' column in df?",
  "notebook": "clean.ipynb",
  "setup": {
    "run_cells": [0, 1]
  },
  "success_criteria": {
    "type": "contains_numbers",
    "expected_min": -500,
    "expected_max": 50000,
    "tolerance": 100
  },
  "difficulty": "easy"
}
```

#### Bug Fixing Tasks

**`eval/tasks/bug_fixing/BF-01.json`**
```json
{
  "id": "BF-01",
  "category": "bug_fixing",
  "name": "Fix KeyError",
  "prompt": "Cell 2 has an error. Fix it so the cell executes successfully.",
  "notebook": "broken.ipynb",
  "setup": {
    "run_cells": [0, 1]
  },
  "success_criteria": {
    "type": "cell_executes",
    "cell_index": 2
  },
  "difficulty": "easy"
}
```

#### State Recovery Tasks

**`eval/tasks/state_recovery/SR-01.json`**
```json
{
  "id": "SR-01",
  "category": "state_recovery",
  "name": "Fix Inconsistent State",
  "prompt": "This notebook has inconsistent state. The outputs don't match the code. Fix it so the notebook is in a consistent state.",
  "notebook": "messy.ipynb",
  "setup": {},
  "success_criteria": {
    "type": "notebook_validates",
    "allow_warnings": false
  },
  "difficulty": "medium"
}
```

#### Dependency Reasoning Tasks

**`eval/tasks/dependency_reasoning/DR-01.json`**
```json
{
  "id": "DR-01",
  "category": "dependency_reasoning",
  "name": "Identify Affected Cells",
  "prompt": "If I modify Cell 1 (the data loading cell), which other cells would need to be re-run? List the cell numbers.",
  "notebook": "complex.ipynb",
  "setup": {
    "run_cells": [0, 1, 2, 3, 4, 5, 6]
  },
  "success_criteria": {
    "type": "contains_all",
    "expected": ["2", "3", "4", "5", "6"]
  },
  "difficulty": "medium"
}
```

#### Reproducibility Tasks

**`eval/tasks/reproducibility/RP-01.json`**
```json
{
  "id": "RP-01",
  "category": "reproducibility",
  "name": "Identify Reproducibility Issues",
  "prompt": "This notebook has reproducibility issues. What problems would prevent it from running on another machine? List the issues.",
  "notebook": "unreproducible.ipynb",
  "setup": {},
  "success_criteria": {
    "type": "contains_any",
    "expected": ["hardcoded path", "random seed", "environment variable", "API_KEY"]
  },
  "difficulty": "medium"
}
```

---

### 0.4 Build Eval Harness

#### `eval/harness/runner.py`

```python
"""Main evaluation runner."""

import json
import time
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional

from .agent import AgentWrapper
from .checker import check_success
from .metrics import compute_metrics


@dataclass
class TaskResult:
    task_id: str
    completed: bool
    first_try_success: bool
    iterations: int
    errors: int
    tokens_used: int
    elapsed_seconds: float
    transcript: list[dict]


def load_task(task_path: Path) -> dict:
    """Load task definition from JSON."""
    with open(task_path) as f:
        return json.load(f)


def run_task(
    task: dict,
    agent: AgentWrapper,
    notebooks_dir: Path,
    max_iterations: int = 20
) -> TaskResult:
    """Run a single evaluation task."""
    
    # Load notebook
    notebook_path = notebooks_dir / task["notebook"]
    
    # Setup (run prerequisite cells if needed)
    if task.get("setup", {}).get("run_cells"):
        agent.setup_notebook(notebook_path, task["setup"]["run_cells"])
    
    # Run agent
    start = time.time()
    transcript = agent.run(
        prompt=task["prompt"],
        notebook_path=notebook_path,
        max_iterations=max_iterations
    )
    elapsed = time.time() - start
    
    # Check success
    completed = check_success(
        task["success_criteria"],
        notebook_path,
        transcript
    )
    
    # Count errors in transcript
    errors = sum(1 for t in transcript if t.get("type") == "error")
    first_try = errors == 0 and completed
    
    return TaskResult(
        task_id=task["id"],
        completed=completed,
        first_try_success=first_try,
        iterations=len(transcript),
        errors=errors,
        tokens_used=sum(t.get("tokens", 0) for t in transcript),
        elapsed_seconds=elapsed,
        transcript=transcript
    )


def run_evaluation(
    tasks_dir: Path,
    notebooks_dir: Path,
    output_dir: Path,
    with_dasa: bool = False,
    runs_per_task: int = 3
) -> dict:
    """Run full evaluation suite."""
    
    agent = AgentWrapper(with_dasa=with_dasa)
    results = []
    
    # Find all task files
    task_files = list(tasks_dir.glob("**/*.json"))
    
    for task_file in task_files:
        task = load_task(task_file)
        
        for run_num in range(runs_per_task):
            print(f"Running {task['id']} (run {run_num + 1}/{runs_per_task})...")
            result = run_task(task, agent, notebooks_dir)
            result_dict = asdict(result)
            result_dict["run_number"] = run_num
            result_dict["with_dasa"] = with_dasa
            results.append(result_dict)
    
    # Save results
    output_file = output_dir / f"results_{'with' if with_dasa else 'without'}_dasa.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    
    # Compute and return metrics
    return compute_metrics(results)
```

#### `eval/harness/checker.py`

```python
"""Success criteria checkers."""

import json
import re
from pathlib import Path


def check_success(criteria: dict, notebook_path: Path, transcript: list) -> bool:
    """Check if task success criteria are met."""
    
    criteria_type = criteria["type"]
    
    if criteria_type == "contains_all":
        return check_contains_all(criteria["expected"], transcript)
    
    elif criteria_type == "contains_any":
        return check_contains_any(criteria["expected"], transcript)
    
    elif criteria_type == "cell_executes":
        return check_cell_executes(criteria["cell_index"], notebook_path)
    
    elif criteria_type == "notebook_validates":
        return check_notebook_validates(notebook_path, criteria.get("allow_warnings", True))
    
    elif criteria_type == "contains_numbers":
        return check_contains_numbers(criteria, transcript)
    
    else:
        raise ValueError(f"Unknown criteria type: {criteria_type}")


def check_contains_all(expected: list, transcript: list) -> bool:
    """Check if agent response contains all expected strings."""
    # Get final agent response
    final_response = get_final_response(transcript)
    if not final_response:
        return False
    
    response_lower = final_response.lower()
    return all(str(e).lower() in response_lower for e in expected)


def check_contains_any(expected: list, transcript: list) -> bool:
    """Check if agent response contains any expected string."""
    final_response = get_final_response(transcript)
    if not final_response:
        return False
    
    response_lower = final_response.lower()
    return any(str(e).lower() in response_lower for e in expected)


def check_cell_executes(cell_index: int, notebook_path: Path) -> bool:
    """Check if a specific cell executes without error."""
    # This would need to actually run the cell
    # For now, return False as placeholder
    # TODO: Implement with kernel execution
    return False


def check_notebook_validates(notebook_path: Path, allow_warnings: bool) -> bool:
    """Check if notebook passes validation."""
    # This would run `dasa validate`
    # For baseline (no DASA), always return False
    # TODO: Implement with dasa validate
    return False


def check_contains_numbers(criteria: dict, transcript: list) -> bool:
    """Check if response contains expected numbers within tolerance."""
    final_response = get_final_response(transcript)
    if not final_response:
        return False
    
    # Extract numbers from response
    numbers = [float(n) for n in re.findall(r'-?\d+\.?\d*', final_response)]
    
    expected_min = criteria.get("expected_min")
    expected_max = criteria.get("expected_max")
    tolerance = criteria.get("tolerance", 0)
    
    found_min = any(abs(n - expected_min) <= tolerance for n in numbers) if expected_min else True
    found_max = any(abs(n - expected_max) <= tolerance for n in numbers) if expected_max else True
    
    return found_min and found_max


def get_final_response(transcript: list) -> str:
    """Extract final agent response from transcript."""
    for entry in reversed(transcript):
        if entry.get("type") == "response":
            return entry.get("content", "")
    return ""
```

#### `eval/harness/metrics.py`

```python
"""Metric computation."""

from collections import defaultdict
import statistics


def compute_metrics(results: list) -> dict:
    """Compute aggregate metrics from results."""
    
    if not results:
        return {}
    
    # Group by category
    by_category = defaultdict(list)
    for r in results:
        # Extract category from task_id (e.g., "DU-01" -> "DU")
        category = r["task_id"].split("-")[0]
        by_category[category].append(r)
    
    metrics = {
        "overall": compute_category_metrics(results),
        "by_category": {
            cat: compute_category_metrics(cat_results)
            for cat, cat_results in by_category.items()
        }
    }
    
    return metrics


def compute_category_metrics(results: list) -> dict:
    """Compute metrics for a set of results."""
    
    n = len(results)
    if n == 0:
        return {}
    
    completed = [r for r in results if r["completed"]]
    first_try = [r for r in results if r["first_try_success"]]
    
    return {
        "total_runs": n,
        "completion_rate": len(completed) / n,
        "first_try_rate": len(first_try) / n,
        "avg_iterations": statistics.mean(r["iterations"] for r in results),
        "avg_errors": statistics.mean(r["errors"] for r in results),
        "avg_tokens": statistics.mean(r["tokens_used"] for r in results),
        "avg_time_seconds": statistics.mean(r["elapsed_seconds"] for r in results),
    }


def compare_conditions(baseline: dict, with_dasa: dict) -> dict:
    """Compare metrics between baseline and with-DASA conditions."""
    
    comparison = {}
    
    for key in baseline.get("overall", {}):
        if key == "total_runs":
            continue
        
        base_val = baseline["overall"].get(key, 0)
        dasa_val = with_dasa["overall"].get(key, 0)
        
        if base_val > 0:
            change = (dasa_val - base_val) / base_val * 100
        else:
            change = 0
        
        comparison[key] = {
            "baseline": base_val,
            "with_dasa": dasa_val,
            "change_percent": change
        }
    
    return comparison
```

---

### 0.5 Establish Baseline

Run evaluation without DASA to establish baseline metrics:

```bash
cd eval
python -m harness.runner --condition baseline --output results/baseline.json
```

**Expected baseline results (estimates):**

| Category | Completion Rate | First-Try Rate |
|----------|-----------------|----------------|
| Data Understanding (DU) | ~50% | ~20% |
| Bug Fixing (BF) | ~60% | ~30% |
| Visualization (VZ) | ~40% | ~15% |
| State Recovery (SR) | ~30% | ~10% |
| Dependency Reasoning (DR) | ~40% | ~15% |
| Reproducibility (RP) | ~35% | ~10% |
| **Overall** | **~43%** | **~17%** |

Document actual baseline results in `eval/results/BASELINE.md`.

---

## Acceptance Criteria

- [ ] All 5 test notebooks created and valid JSON
- [ ] Test data `sales.csv` created with required characteristics
- [ ] At least 12 task definitions (2 per category)
- [ ] Eval harness runs without errors
- [ ] Baseline results documented

---

## Files Created

```
eval/
├── README.md
├── data/
│   └── sales.csv
├── notebooks/
│   ├── clean.ipynb
│   ├── messy.ipynb
│   ├── broken.ipynb
│   ├── complex.ipynb
│   └── unreproducible.ipynb
├── tasks/
│   ├── data_understanding/
│   │   ├── DU-01.json
│   │   └── DU-02.json
│   ├── bug_fixing/
│   │   └── BF-01.json
│   ├── visualization/
│   │   └── VZ-01.json
│   ├── state_recovery/
│   │   └── SR-01.json
│   ├── dependency_reasoning/
│   │   └── DR-01.json
│   └── reproducibility/
│       └── RP-01.json
├── harness/
│   ├── __init__.py
│   ├── runner.py
│   ├── agent.py
│   ├── checker.py
│   └── metrics.py
└── results/
    └── BASELINE.md
```

# DASA Evaluation Infrastructure

This directory contains the evaluation harness for the Data Science Agent (DASA) project. It provides a standardized framework for measuring agent capabilities across six task categories.

## Directory Structure

```
eval/
├── README.md                 # This file
├── data/
│   └── sales.csv             # Synthetic sales dataset (~1000 rows)
├── notebooks/                # Test notebooks in various states
│   ├── clean.ipynb           # Properly executed, no issues
│   ├── messy.ipynb           # Out-of-order execution
│   ├── broken.ipynb          # Contains runtime errors
│   ├── complex.ipynb         # Multi-step ML pipeline with dependencies
│   └── unreproducible.ipynb  # Reproducibility anti-patterns
├── tasks/                    # Task definitions (JSON)
│   ├── data_understanding/   # DU-01 through DU-03
│   ├── bug_fixing/           # BF-01 through BF-02
│   ├── visualization/        # VZ-01
│   ├── state_recovery/       # SR-01 through SR-02
│   ├── dependency_reasoning/ # DR-01 through DR-02
│   └── reproducibility/      # RP-01 through RP-02
├── harness/                  # Python evaluation harness
│   ├── __init__.py
│   ├── runner.py             # Orchestrates task discovery and execution
│   ├── agent.py              # Abstract agent wrapper interface
│   ├── checker.py            # Success-criteria checkers
│   └── metrics.py            # Metrics collection and reporting
└── results/                  # Evaluation run outputs (git-ignored contents)
    └── .gitkeep
```

## Task Categories

| Category               | Tasks | Description                                      |
|------------------------|-------|--------------------------------------------------|
| data_understanding     | 3     | Questions about dataset structure and content     |
| bug_fixing             | 2     | Fixing runtime errors in notebook cells           |
| visualization          | 1     | Creating or modifying charts and plots            |
| state_recovery         | 2     | Restoring consistent notebook execution state     |
| dependency_reasoning   | 2     | Reasoning about cell dependencies and ordering    |
| reproducibility        | 2     | Identifying and fixing reproducibility issues     |

## Usage

```python
from eval.harness import EvalRunner, MetricsCollector
from eval.harness.agent import DummyAgent  # Replace with your agent

agent = DummyAgent()
runner = EvalRunner(
    tasks_dir="eval/tasks",
    notebooks_dir="eval/notebooks",
    agent=agent,
    results_dir="eval/results",
)

collector = runner.run_all()
collector.print_summary()
```

## Task Definition Format

Each task JSON file contains:

- **id**: Unique task identifier (e.g., `DU-01`)
- **category**: Task category string
- **name**: Human-readable task name
- **prompt**: The instruction given to the agent
- **notebook**: Filename of the notebook to operate on
- **setup**: Context and setup information
- **success_criteria**: How to evaluate the agent's output
- **difficulty**: `easy`, `medium`, or `hard`

## Success Criteria Types

- `contains_all`: Agent response must contain all specified strings
- `contains_any`: Agent response must contain at least one specified string
- `contains_numbers`: Agent response must contain numbers within tolerance
- `cell_executes`: A specific notebook cell must execute without error
- `notebook_validates`: Notebook must have sequential execution counts

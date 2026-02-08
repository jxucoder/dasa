# The `.dasa` Notebook Format (Exploration)

> **Status: Explored, not pursuing.** This was a design exploration into what an agent-native notebook format could look like. After deeper analysis, we concluded that a new format isn't the right approach — the problems are better solved with tools and persistent context on top of existing formats. See [DESIGN.md](DESIGN.md) for the current design direction.

A plain-text, agent-native notebook format designed from first principles.

## Philosophy

Current notebook formats were designed for humans clicking cells in a browser. The `.dasa` format is designed for a different world — one where AI agents are the primary operators and humans are the primary readers.

**Core insight:** A notebook is not a program. It is a *workspace* that produces an *artifact*. Current formats collapse these into one thing and fail at both. The `.dasa` format keeps them separate.

| Layer | What it captures | Current notebooks | `.dasa` format |
|-------|-----------------|-------------------|----------------|
| **Artifact** | The pipeline — the DAG of transforms from raw data to result | Mixed in with everything else | Explicit: `source`, `transform`, `train` cells |
| **Workspace** | Exploration — queries, scratch work, dead ends | Also cells, indistinguishable from pipeline | Explicit: `query` cells marked `ephemeral` |
| **Context** | Intent, decisions, what was tried | Markdown cells (maybe), usually absent | Explicit: `narrative` cells + `journal` |

The format makes these layers *structurally distinct*, not just conventionally different. An agent — or a human — can immediately tell what's pipeline, what's exploration, and what's context.

## Design Principles

1. **Explicit over inferred.** Dependencies, schemas, costs, and intents are *declared*, not recovered by analysis after the fact.
2. **Typed cells.** Not every cell is the same kind of thing. The format knows the difference between a transform, a query, and an assertion.
3. **Contracts over comments.** Cell metadata is structured and machine-readable, not free-text hints.
4. **Plain text.** No JSON wrapping, no base64 outputs, no binary. Readable by humans, LLMs, `grep`, and `diff`.
5. **Outputs are ephemeral.** The file stores *code and contracts*, not results. Outputs live in a runtime cache, never in the source file.
6. **Journal is first-class.** The history of decisions — what was tried, what failed, what was chosen — is part of the format, not lost when cells are deleted.

## Format Overview

A `.dasa` file is a sequence of **blocks** separated by `===` headers. Each block has a **type**, an optional **name**, an optional **contract** (YAML metadata), and a **body** (Python code or prose).

```
=== type: name ===
key: value
key: value

body content here
```

That's the whole syntax. No nesting, no escaping, no special characters beyond `===`.

---

## File Structure

```
=== notebook ===               ← Document header (exactly one, must be first)
...metadata...

=== source: load_data ===      ← Cell blocks (any number, any order in file)
...contract...                    The pipeline order is determined by dependencies,
                                  not file order.
code

=== transform: clean ===
...contract...

code

=== journal ===                ← Journal (exactly one, must be last)
...entries...
```

---

## Document Header

The first block is always `=== notebook ===`. It declares the notebook's identity and requirements.

```
=== notebook ===
name: churn_prediction
intent: Predict user churn from behavioral and engagement data
python: ">=3.10"
requires:
  - pandas>=2.0
  - scikit-learn>=1.3
  - matplotlib>=3.7
tags: [ml, classification, churn]
authors: [jxu]
created: 2026-02-08
```

### Required fields

| Field | Description |
|-------|-------------|
| `name` | Identifier for the notebook (used in caching, logs) |
| `intent` | One-line description of *what this notebook is trying to do* |

### Optional fields

| Field | Description |
|-------|-------------|
| `python` | Python version constraint |
| `requires` | Package dependencies (PEP 508 format) |
| `tags` | Freeform tags for discovery |
| `authors` | Contributors |
| `created` | Creation date |

The `intent` field is the most important piece of metadata for an agent. It answers "why does this notebook exist?" before a single cell is read.

---

## Cell Types

There are seven cell types grouped into three layers.

### Artifact Layer (the pipeline)

These cells form the DAG. They compose into a reproducible pipeline from data to result.

#### `source`

Loads data from an external origin. The entry point of the pipeline.

```
=== source: load_data ===
produces: {df: DataFrame}
schema:
  df:
    columns:
      user_id: int
      name: str
      age: int
      score: float
      region: str
      created: datetime
    rows: ~50000
origin: data/users.csv
cost: cheap
pure: false

import pandas as pd
df = pd.read_csv("data/users.csv", parse_dates=["created"])
```

- `origin` — where the data comes from (file path, URL, database, API)
- `schema` — declared structure of what's produced
- Always `pure: false` (reads external state)

#### `transform`

Pure data transformation. The workhorse of the pipeline.

```
=== transform: clean ===
requires: {df: DataFrame}
produces: {df_clean: DataFrame}
invariant: len(df_clean) <= len(df)
cost: cheap

df_clean = df.dropna(subset=["age", "score"])
df_clean = df_clean[df_clean.score.between(0, 1)]
```

- `requires` — input variables and their types
- `produces` — output variables and their types
- `invariant` — optional condition that should hold after execution (checked at runtime)
- `cost` — `cheap` (seconds), `moderate` (minutes), `expensive` (hours)
- Implicitly `pure: true` — same inputs always produce same outputs

#### `train`

A specialized transform that produces a model. Separated from `transform` because it has different agent semantics: expensive, non-trivial to re-run, often non-deterministic without explicit seeds.

```
=== train: churn_model ===
requires: {X_train: DataFrame, y_train: Series}
produces: {model: LogisticRegression}
cost: expensive
seed: 42

from sklearn.linear_model import LogisticRegression
model = LogisticRegression(random_state=42, max_iter=1000)
model.fit(X_train, y_train)
```

- `seed` — random seed for reproducibility (the runtime can also enforce this)
- An agent seeing `train` knows: don't re-run this casually, cache the result, check before invalidating

#### `effect`

A cell with intentional side effects — writes to disk, calls an API, modifies a database. Separated because agents must treat these differently from pure computations.

```
=== effect: save_model ===
requires: {model: LogisticRegression}
action: write model artifact to disk
destructive: false
idempotent: true

import joblib
joblib.dump(model, "artifacts/churn_model.pkl")
```

- `action` — human/agent-readable description of what the side effect does
- `destructive` — does it destroy/overwrite something? (false = safe to retry)
- `idempotent` — is running it twice the same as running it once?

An agent knows: `destructive: false, idempotent: true` means it's safe to re-run. `destructive: true, idempotent: false` means ask the human first.

### Workspace Layer (exploration)

These cells are not part of the pipeline. They're tools for understanding.

#### `query`

Asks a question about the data. Produces output for the human/agent to read, but doesn't change state or contribute to the pipeline.

```
=== query: score_distribution ===
requires: {df_clean: DataFrame}

print(df_clean.score.describe())
df_clean.score.hist(bins=50, title="Score Distribution")
print(f"\nSkewness: {df_clean.score.skew():.3f}")
```

- Always ephemeral — not part of the pipeline DAG
- Can be re-run freely (cheap, no side effects)
- An agent can skip all `query` cells and the pipeline still works
- Useful for agents: running queries to understand data before making changes

#### `assertion`

A checkpoint that verifies something is true. Like a test, but inline with the analysis.

```
=== assertion: data_quality ===
requires: {df_clean: DataFrame}
checks:
  - df_clean.age.notna().all()             # no nulls in age
  - len(df_clean) > 1000                    # enough data
  - df_clean.score.between(0, 1).all()      # scores normalized
  - df_clean.region.nunique() == 4           # all regions present
```

- `checks` — list of boolean expressions that must all be true
- No code body needed if `checks` is provided — the runtime evaluates them directly
- Can also have a code body for complex assertions:

```
=== assertion: model_quality ===
requires: {model: LogisticRegression, X_test: DataFrame, y_test: Series}

accuracy = model.score(X_test, y_test)
assert accuracy > 0.7, f"Model accuracy {accuracy:.3f} below threshold 0.7"
```

Assertions serve as **contracts between cells**. When an agent modifies a `transform`, the downstream `assertion` tells it whether the change was correct — without the agent having to guess what "correct" means.

### Context Layer (understanding)

#### `narrative`

Free-form text that explains what's happening and why. Like markdown cells, but positioned as context, not code.

```
=== narrative ===
After cleaning, we have ~47k rows. The score distribution is roughly
normal with slight right skew. No obvious outliers remain.

We chose logistic regression over random forest because:
- Random forest overfit badly (0.91 train / 0.72 test)
- Logistic regression generalizes better (0.84 test)
- Interpretability matters for this use case (stakeholder requirement)
```

- No contract, no code — just prose
- Critical for agents: this is the "why" that code alone doesn't capture
- Can appear anywhere in the file to provide context near the relevant cells

---

## Cell Contracts

Every artifact cell (source, transform, train, effect) has a **contract** — structured metadata in the header between the `===` line and the code body.

### Core contract fields

| Field | Used by | Description |
|-------|---------|-------------|
| `requires` | transform, train, effect, query, assertion | Input variables and expected types |
| `produces` | source, transform, train | Output variables and expected types |
| `schema` | source, transform | Detailed structure of produced data |
| `cost` | all artifact cells | `cheap` / `moderate` / `expensive` |
| `pure` | all artifact cells | `true` (default) or `false` |
| `invariant` | transform | Condition that must hold after execution |
| `seed` | train | Random seed for reproducibility |

### Schema declarations

Schemas describe data shape without running anything:

```
schema:
  df:
    columns:
      user_id: int
      name: str
      age: int          # nullable
      score: float      # range [0, 1]
      region: str       # categorical: [North, South, East, West]
      created: datetime
    rows: ~50000
    index: user_id
```

This is intentionally approximate. `rows: ~50000` means "roughly 50k" — it's a hint, not a constraint. The goal is to give agents enough context to write correct code *without executing anything*, not to create a rigid type system.

### The dependency graph

The pipeline's execution order is derived from `requires` / `produces`:

```
source: load_data         →  produces: {df}
transform: clean          →  requires: {df}, produces: {df_clean}
transform: features       →  requires: {df_clean}, produces: {X, y}
train: model              →  requires: {X, y}, produces: {model}
assertion: model_quality  →  requires: {model, X_test, y_test}
effect: save_model        →  requires: {model}
```

This forms a DAG:

```
load_data → clean → features → model → save_model
                                  ↓
                             model_quality
```

The DAG is a *consequence* of the contracts, not something the user draws. Write your cells, declare what they need and produce, and the graph emerges.

---

## The Journal

The last block in the file is the journal — an append-only log of decisions, experiments, and observations.

```
=== journal ===
- 2026-02-08 10:00 | Loaded users.csv, 50k rows, 12 columns
- 2026-02-08 10:15 | Found 4.7% nulls in age column
- 2026-02-08 10:20 | Tried median imputation → skewed downstream distributions
- 2026-02-08 10:25 | Switched to dropping null rows, lost ~2.3k rows, acceptable
- 2026-02-08 10:45 | Random forest: 0.91 train / 0.72 test — overfit, abandoned
- 2026-02-08 11:00 | Logistic regression: 0.82 train / 0.84 test — much better
- 2026-02-08 11:30 | Added days_since_signup feature, test accuracy → 0.86
- 2026-02-08 11:45 | DECISION: Ship logistic regression, accuracy sufficient for v1
```

### Why the journal matters

When an agent picks up this notebook, it can read the journal and immediately understand:
- What approaches were already tried (don't suggest random forest again)
- Why decisions were made (logistic regression for interpretability)
- What the human cares about (generalization over train accuracy)
- Where the analysis currently is (ready to ship)

Without the journal, the agent would have to reverse-engineer all of this from code comments (if any exist) and cell outputs (which might be stale).

### Journal conventions

- **Append-only.** Never edit or delete entries. The journal is a log, not a document.
- **Both humans and agents write to it.** When an agent makes a significant decision (tried an approach, chose a parameter), it appends an entry.
- **Entries are timestamped.** Provides temporal context for the analysis process.
- **Prefix decisions with `DECISION:`** to make them scannable.
- **Include quantitative results** when available (accuracy, row counts, timings).

---

## Execution Model

### Pipeline execution

The runtime executes the pipeline (artifact cells) in dependency order:

```
1. Resolve the DAG from requires/produces
2. Topological sort
3. Execute each cell in order
4. After each cell:
   a. Validate invariants (if declared)
   b. Run downstream assertions
   c. Cache the result (keyed by cell name + input hash)
5. If an assertion fails: stop, report, don't continue
```

### Selective re-execution

When a cell is modified:

```
1. Identify the modified cell
2. Find all downstream cells in the DAG
3. Invalidate their caches
4. Re-execute only the invalidated subgraph
5. Re-run affected assertions
```

An agent modifying `transform: clean` knows exactly what will re-run (everything downstream) and what won't (everything upstream).

### Query execution

Queries run on demand, outside the pipeline:

```
1. Check that all required variables exist (from pipeline cache)
2. Execute the query cell
3. Display output
4. Discard — don't cache, don't affect pipeline state
```

### Cost-aware execution

The runtime uses `cost` annotations to make smart decisions:

| Scenario | Behavior |
|----------|----------|
| Re-run `cheap` cell | Just do it |
| Re-run `moderate` cell | Check cache first, re-run if invalidated |
| Re-run `expensive` cell | Warn before executing, offer to use cache |
| Agent re-runs `expensive` cell | Require explicit confirmation from human |

---

## Agent Interface

The `.dasa` format is designed so agents can work with notebooks using simple, predictable operations. Here's what an agent can do and how:

### Read the notebook

The file is plain text. An agent can read it directly — no parsing library needed for basic understanding. The `===` headers, YAML contracts, and code bodies are immediately legible in an LLM context window.

### Understand the pipeline

```
1. Read the notebook header → understand intent
2. Scan cell headers → see the full pipeline structure (types, names, contracts)
3. Read the journal → understand history and decisions
4. Read specific cell bodies → understand implementation details
```

An agent can understand the pipeline *structure* without reading any code bodies. The contracts carry enough information.

### Modify the notebook

Adding a cell:
```
1. Choose the cell type (transform, query, etc.)
2. Declare the contract (requires, produces, schema)
3. Write the code body
4. The runtime re-derives the DAG
```

Editing a cell:
```
1. Modify the code body (or contract)
2. The runtime identifies affected downstream cells
3. Re-executes the invalidated subgraph
4. Re-checks assertions
```

### Execute selectively

An agent can request:
- **Run the pipeline** — execute all artifact cells in dependency order
- **Run a query** — execute a specific query cell for exploration
- **Check assertions** — run all assertions without re-executing the pipeline
- **Re-run from cell X** — invalidate cell X and everything downstream, re-execute

### Add a journal entry

After making significant changes, the agent appends to the journal:

```
- 2026-02-08 14:00 | [agent] Replaced median imputation with KNN imputation per user request, test accuracy improved 0.84 → 0.87
```

---

## Interoperability

### Import from Jupyter (.ipynb)

```bash
dasa convert notebook.ipynb --output notebook.dasa
```

The converter:
1. Extracts code and markdown cells
2. Infers cell types via heuristics:
   - Cells with `pd.read_csv`, `open()` → `source`
   - Cells with `.fit()` → `train`
   - Cells ending in `.head()`, `.describe()`, `.plot()` → `query`
   - Cells with only `assert` → `assertion`
   - Markdown cells → `narrative`
   - Everything else → `transform`
3. Infers `requires`/`produces` via AST analysis
4. Infers schemas from execution (if kernel available)
5. Generates contracts (marked as inferred, human should verify)

### Export to Jupyter (.ipynb)

```bash
dasa convert notebook.dasa --output notebook.ipynb
```

- Artifact cells become code cells (in DAG order)
- Query cells become code cells (after their dependencies)
- Narrative cells become markdown cells
- Assertions become code cells with `assert` statements
- Journal becomes a final markdown cell
- Contracts become structured comments at the top of each cell

### Export to Python (.py)

```bash
dasa convert notebook.dasa --output pipeline.py --pipeline-only
```

- Extracts only artifact cells (source, transform, train, effect)
- Wraps each in a function
- Chains them in dependency order
- Produces a runnable pipeline script
- Drops queries, narratives, journal (they're workspace, not artifact)

---

## Runtime Cache

The `.dasa` format does not store outputs. A companion `.dasa_cache/` directory holds runtime state:

```
.dasa_cache/
├── outputs/                    # Cached cell outputs
│   ├── load_data.pkl           # Keyed by cell name
│   ├── clean.pkl
│   └── churn_model.pkl
├── hashes/                     # Input hashes for cache invalidation
│   ├── load_data.sha256
│   └── clean.sha256
├── history/                    # Execution history
│   └── 2026-02-08T10:00.log
└── snapshots/                  # Point-in-time full snapshots
    └── 001_before_refactor/
```

- The `.dasa` file is always the source of truth
- The cache is derived, disposable, and `.gitignore`-able
- Sharing a `.dasa` file without the cache is like sharing source code — it's complete, just needs execution to produce results

---

## Complete Example

```
=== notebook ===
name: churn_prediction
intent: Predict which users will churn using behavioral data
python: ">=3.10"
requires:
  - pandas>=2.0
  - scikit-learn>=1.3
  - matplotlib>=3.7

=== source: load_data ===
produces: {df: DataFrame}
schema:
  df:
    columns:
      user_id: int
      name: str
      age: int
      score: float
      region: str
      last_login: datetime
      churned: int
    rows: ~50000
origin: data/users.csv
cost: cheap

import pandas as pd
df = pd.read_csv("data/users.csv", parse_dates=["last_login"])

=== query: initial_look ===
requires: {df: DataFrame}

print(f"Shape: {df.shape}")
print(f"\nNull counts:\n{df.isnull().sum()}")
print(f"\nChurn rate: {df.churned.mean():.1%}")

=== narrative ===
About 23% churn rate — imbalanced but not extreme.
Nulls only in age (4.7%) and score (0.3%). Manageable.

=== transform: clean ===
requires: {df: DataFrame}
produces: {df_clean: DataFrame}
invariant: len(df_clean) >= len(df) * 0.9
cost: cheap

df_clean = df.dropna(subset=["age", "score"])
df_clean = df_clean[df_clean.age.between(18, 100)]

=== assertion: clean_quality ===
requires: {df_clean: DataFrame}
checks:
  - df_clean.age.notna().all()
  - df_clean.score.notna().all()
  - df_clean.age.between(18, 100).all()
  - len(df_clean) > 40000

=== transform: features ===
requires: {df_clean: DataFrame}
produces: {X: DataFrame, y: Series}
schema:
  X:
    columns:
      age: float
      score: float
      days_inactive: float
  y:
    dtype: int
    values: [0, 1]
cost: cheap

X = df_clean[["age", "score"]].copy()
X["days_inactive"] = (pd.Timestamp.now() - df_clean.last_login).dt.days
y = df_clean["churned"]

=== transform: split ===
requires: {X: DataFrame, y: Series}
produces: {X_train: DataFrame, X_test: DataFrame, y_train: Series, y_test: Series}
seed: 42
cost: cheap

from sklearn.model_selection import train_test_split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

=== train: churn_model ===
requires: {X_train: DataFrame, y_train: Series}
produces: {model: LogisticRegression}
cost: moderate
seed: 42

from sklearn.linear_model import LogisticRegression
model = LogisticRegression(random_state=42, max_iter=1000)
model.fit(X_train, y_train)

=== assertion: model_quality ===
requires: {model: LogisticRegression, X_test: DataFrame, y_test: Series}

accuracy = model.score(X_test, y_test)
assert accuracy > 0.75, f"Accuracy {accuracy:.3f} below 0.75 threshold"

=== query: evaluate ===
requires: {model: LogisticRegression, X_test: DataFrame, y_test: Series}

from sklearn.metrics import classification_report, confusion_matrix
print(classification_report(y_test, model.predict(X_test)))
print(f"\nConfusion matrix:\n{confusion_matrix(y_test, model.predict(X_test))}")

=== query: feature_importance ===
requires: {model: LogisticRegression, X: DataFrame}

import matplotlib.pyplot as plt
coefs = pd.Series(model.coef_[0], index=X.columns)
coefs.sort_values().plot(kind="barh", title="Feature Importance (coefficients)")
plt.tight_layout()

=== narrative ===
days_inactive is the strongest predictor — makes sense.
Score has moderate negative correlation with churn.
Age is weak but non-zero.

Model hits 0.86 accuracy on test set. Good enough for v1 — the goal
is to flag at-risk users for the retention team, not to be perfect.

=== effect: save_model ===
requires: {model: LogisticRegression}
action: Save trained model to artifacts directory
destructive: false
idempotent: true

import joblib
joblib.dump(model, "artifacts/churn_model_v1.pkl")
print("Model saved to artifacts/churn_model_v1.pkl")

=== journal ===
- 2026-02-08 10:00 | Started analysis. Loaded users.csv, 50k rows
- 2026-02-08 10:15 | EDA: 23% churn rate, nulls in age (4.7%) and score (0.3%)
- 2026-02-08 10:25 | Dropped null rows. Lost ~2.3k rows, 47.5k remain
- 2026-02-08 10:40 | Tried random forest: 0.91 train / 0.72 test — overfit badly
- 2026-02-08 10:50 | Tried XGBoost: 0.88 train / 0.78 test — better but slow
- 2026-02-08 11:00 | Tried logistic regression: 0.85 train / 0.84 test — best generalization
- 2026-02-08 11:20 | Added days_inactive feature: test accuracy 0.84 → 0.86
- 2026-02-08 11:30 | DECISION: Ship logistic regression v1. Accuracy sufficient for retention flagging
- 2026-02-08 11:45 | Saved model artifact. Ready for deployment review
```

---

## Open Questions

These are design decisions that need further exploration:

1. **Multi-language support.** The current spec assumes Python. Should cells declare their language? (`lang: python`, `lang: sql`, `lang: r`). The format itself is language-agnostic — the question is whether the runtime should be.

2. **Parameterization.** Should notebooks accept parameters? (`dasa run notebook.dasa --param threshold=0.5`). This would enable notebooks-as-functions, composable into larger pipelines.

3. **Forking.** Data science often involves trying multiple approaches in parallel (try 3 different models, compare). The DAG model doesn't capture this well. Should the format support branches? (`=== branch: approach_a ===` / `=== branch: approach_b ===`)

4. **Schema evolution.** When upstream data changes (new column added to CSV), how do declared schemas update? Auto-detection on next run? Manual update? Hybrid?

5. **Collaboration.** How do two people work on the same `.dasa` notebook? The plain-text format makes git merges much easier than JSON, but the journal could still conflict. Should journals be per-author files?

6. **Large data.** The format assumes data fits in memory. For large-scale data science (Spark, Dask), the execution model needs distributed caching and remote execution. This is a runtime concern, not a format concern, but worth noting.

7. **Visualization storage.** Queries that produce plots — should the runtime cache the rendered images? Where? The current design says `.dasa_cache/`, but agents might want to reference a specific plot ("the histogram from query:score_distribution").

# DASA Sprints

Implementation is divided into sprints, starting with evaluation infrastructure (Sprint 0) to enable test-driven development.

## Sprint Overview

| Sprint | Name | Duration | Focus | Deliverables |
|--------|------|----------|-------|--------------|
| **0** | [Evaluation](SPRINT-00.md) | 2-3 days | Test infrastructure | Test notebooks, tasks, eval harness, baseline |
| **1** | [Setup & Core](SPRINT-01.md) | 2-3 days | Foundation | Package, skill, adapters, kernel, parser |
| **2** | [Understanding](SPRINT-02.md) | 3-4 days | MVP Core | `profile`, `validate`, `deps` |
| **3** | [Execution](SPRINT-03.md) | 2-3 days | MVP Complete | `run`, `replay` |
| **4** | [State](SPRINT-04.md) | 2 days | Enhancement | `vars`, `stale`, `kernel` |
| **5** | [Manipulation](SPRINT-05.md) | 2 days | Enhancement | `add`, `edit`, `delete`, `move` |
| **6** | [Info & Async](SPRINT-06.md) | 3 days | Nice-to-have | `info`, `cells`, `outputs`, async |
| **7** | [Extensions](SPRINT-07.md) | 3-4 days | Stretch | Marimo, MCP, rich outputs |

## MVP Definition

**MVP = Sprint 0 + Sprint 1 + Sprint 2 + Sprint 3**

| Sprint | Eval Impact |
|--------|-------------|
| Sprint 0 | Establishes baseline metrics |
| Sprint 1 | Infrastructure (no direct eval impact) |
| Sprint 2 | Improves DU, SR, DR tasks |
| Sprint 3 | Improves BF, RP tasks |

**MVP Success:** Overall completion rate >70% with +25% improvement over baseline.

## Sprint Flow

```
Sprint 0: Eval Infrastructure
    │
    ├── Create test notebooks (clean, messy, broken, complex, unreproducible)
    ├── Create task definitions (12-18 tasks)
    ├── Build eval harness
    └── Establish baseline metrics
    │
    ▼
Sprint 1: Setup & Core
    │
    ├── pyproject.toml, package structure
    ├── Agent skill (SKILL.md)
    ├── Jupyter adapter
    ├── Kernel manager
    └── AST parser
    │
    ▼
Sprint 2: Understanding Tools  ──── Eval checkpoint (DU, SR, DR improvement)
    │
    ├── dasa profile
    ├── dasa validate
    └── dasa deps
    │
    ▼
Sprint 3: Execution Tools  ──── MVP Eval checkpoint (all categories)
    │
    ├── dasa run
    └── dasa replay
    │
    ▼
Sprint 4-7: Enhancements & Extensions
```

## Getting Started

Start with Sprint 0:

```bash
# Read the sprint doc
cat docs/sprints/SPRINT-00.md

# Create eval directory structure
mkdir -p eval/{notebooks,data,tasks,harness,results}
```

## Evaluation Checkpoints

| Checkpoint | After Sprint | Expected Improvement |
|------------|--------------|---------------------|
| Baseline | 0 | ~43% completion (no DASA) |
| Understanding | 2 | ~56% completion (+13%) |
| MVP Complete | 3 | ~70% completion (+27%) |
| Full | 6 | ~80% completion (+37%) |

## Sprint Dependencies

```
Sprint 0 ───────────────────────────────────────────────────┐
    │                                                       │
Sprint 1 ──────────────────────────────────┐               │
    │                                       │               │
Sprint 2 ─────────────────────┐            │               │
    │                          │            │               │
Sprint 3 ────────┐            │            │               │
    │             │            │            │               │
Sprint 4         │            │            │               │
    │             │            │            │               │
Sprint 5         │            │            │               │
    │             │            │            │               │
Sprint 6         │            │            │               │
    │             │            │            │               │
Sprint 7         │            │            │               │
                  │            │            │               │
              (Execution)  (Understanding) (Core)        (Eval)
```

All sprints depend on Sprint 0 (eval) and Sprint 1 (core infrastructure).

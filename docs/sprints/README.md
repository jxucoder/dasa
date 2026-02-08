# DASA Sprints

Implementation is divided into 6 sprints, starting with evaluation infrastructure (Sprint 0) to enable test-driven development.

## Sprint Overview

| Sprint | Name | Duration | Focus | Deliverables |
|--------|------|----------|-------|--------------|
| **0** | [Evaluation](SPRINT-00.md) | 2-3 days | Test infrastructure | Test notebooks, tasks, eval harness, baseline |
| **1** | [Core + Session](SPRINT-01.md) | 3-4 days | Foundation | Package, `.dasa/` session, adapters, kernel, parser, skill |
| **2** | [Eyes](SPRINT-02.md) | 3-4 days | MVP Core | `dasa profile`, `dasa check` |
| **3** | [Hands + Memory](SPRINT-03.md) | 3-4 days | MVP Complete | `dasa run`, `dasa context` |
| **4** | [Multi-Agent](SPRINT-04.md) | 3-4 days | Enhancement | Agent roles, hooks, background execution |
| **5** | [Extensions](SPRINT-05.md) | 3-4 days | Stretch | MCP server, Marimo adapter, replay |

## MVP Definition

**MVP = Sprint 0 + Sprint 1 + Sprint 2 + Sprint 3** (~12-15 days)

| Sprint | Eval Impact |
|--------|-------------|
| Sprint 0 | Establishes baseline metrics |
| Sprint 1 | Infrastructure (no direct eval impact) |
| Sprint 2 | Improves Data Understanding, State Recovery, Dependency Reasoning |
| Sprint 3 | Improves Bug Fixing, Reproducibility; context improves all categories |

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
Sprint 1: Core + Session
    │
    ├── pyproject.toml, package structure
    ├── .dasa/ session (context.yaml, profiles/, log)
    ├── Jupyter adapter, kernel manager
    ├── AST parser, output formatter
    └── Agent skill (SKILL.md)
    │
    ▼
Sprint 2: Eyes  ──── Eval checkpoint (DU, SR, DR improvement)
    │
    ├── dasa profile (data profiling + auto-cache)
    └── dasa check (state + deps + staleness)
    │
    ▼
Sprint 3: Hands + Memory  ──── MVP Eval checkpoint (all categories)
    │
    ├── dasa run (cell execution + rich errors)
    └── dasa context (project memory read/write)
    │
    ▼
Sprint 4: Multi-Agent  ──── Post-MVP
    │
    ├── Agent roles in SKILL.md
    ├── Hook system (auto-profile, auto-log)
    └── Background execution patterns
    │
    ▼
Sprint 5: Extensions  ──── Stretch
    │
    ├── MCP server
    ├── Marimo adapter
    └── Replay / reproducibility verification
```

## Eval Checkpoints

| Checkpoint | After Sprint | Expected Improvement |
|------------|--------------|---------------------|
| Baseline | 0 | ~43% completion (no DASA) |
| Eyes | 2 | ~56% completion (+13 pts) |
| MVP Complete | 3 | ~70% completion (+27 pts) |
| Multi-Agent | 4 | ~78% completion (+35 pts) |

## Sprint Dependencies

```
Sprint 0 (Eval) ─────────────────────────────────────────┐
    │                                                     │
Sprint 1 (Core + Session) ──────────────────────┐        │
    │                                            │        │
Sprint 2 (Eyes) ───────────────────┐            │        │
    │                               │            │        │
Sprint 3 (Hands + Memory) ────┐    │            │        │
    │                          │    │            │        │
Sprint 4 (Multi-Agent)        │    │            │        │
    │                          │    │            │        │
Sprint 5 (Extensions)         │    │            │        │
                           (Execution) (Understanding) (Core) (Eval)
```

All sprints depend on Sprint 0 (eval) and Sprint 1 (core infrastructure).

## Getting Started

Start with Sprint 0:

```bash
# Read the sprint doc
cat docs/sprints/SPRINT-00.md

# Create eval directory structure
mkdir -p eval/{notebooks,data,tasks,harness,results}
```

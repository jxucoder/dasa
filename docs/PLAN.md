# DASA: Data Science Agent

## Overview

An open source toolkit that gives coding agents the specialized capabilities they need for notebook-based data science work — data profiling, state management, execution control, and persistent memory.

**Core insight:** Generic coding agents can read/write files, but data science has unique challenges — invisible data, inconsistent state, complex dependencies, expensive operations, context that evaporates between conversations. DASA provides four commands that solve these problems.

---

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Eval first** | Build evaluation before features | Ensures measurable progress |
| **4 commands** | `profile`, `check`, `run`, `context` | Focused value. See [DESIGN.md](DESIGN.md) |
| **Session persistence** | `.dasa/` folder | Non-invasive, git-friendly, enables multi-agent |
| **Auto-population** | Tools update session automatically | No manual maintenance needed |
| **No cell manipulation** | Skip `add`/`edit`/`delete`/`move` | Agents can already edit JSON files |
| **CLI-first** | Universal bash interface | Works with any agent platform |
| **MCP deferred** | Extension, not MVP | CLI is universal. MCP is optimization |

---

## Implementation Sprints

| Sprint | Name | Duration | Focus | Deliverables |
|--------|------|----------|-------|--------------|
| **0** | [Evaluation](sprints/SPRINT-00.md) | 2-3 days | Test infrastructure | Test notebooks, tasks, eval harness, baseline |
| **1** | [Core + Session](sprints/SPRINT-01.md) | 3-4 days | Foundation | Package, session, adapters, kernel, parser, skill |
| **2** | [Eyes](sprints/SPRINT-02.md) | 3-4 days | MVP Core | `dasa profile`, `dasa check` |
| **3** | [Hands + Memory](sprints/SPRINT-03.md) | 3-4 days | MVP Complete | `dasa run`, `dasa context` |
| **4** | [Multi-Agent](sprints/SPRINT-04.md) | 3-4 days | Enhancement | Agent roles, hooks, background execution |
| **5** | [Extensions](sprints/SPRINT-05.md) | 3-4 days | Stretch | MCP server, Marimo adapter, replay |

See [sprints/README.md](sprints/README.md) for detailed sprint overview and dependencies.

---

## MVP Definition

**MVP = Sprint 0 + Sprint 1 + Sprint 2 + Sprint 3**

With MVP complete, an agent can:
1. **See the data** — `dasa profile` shows columns, types, stats, quality issues
2. **See the notebook state** — `dasa check` shows inconsistencies, dependencies, staleness
3. **Execute safely** — `dasa run` provides rich error context with suggestions
4. **Remember across conversations** — `dasa context` persists goals, approaches, status

And we can **prove it works** with before/after eval metrics.

| Sprint | Eval Impact |
|--------|-------------|
| Sprint 0 | Establishes baseline metrics |
| Sprint 1 | Infrastructure (no direct eval impact) |
| Sprint 2 | Improves DU, SR, DR tasks |
| Sprint 3 | Improves BF, RP tasks; context improves all tasks |

**MVP Success:** Overall completion rate >70% with +25% improvement over baseline.

---

## Development Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                   Test-Driven Development                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Build Eval (Sprint 0)                                   │
│     └── Create test notebooks, tasks, harness               │
│                                                             │
│  2. Establish Baseline                                      │
│     └── Run eval WITHOUT DASA → record metrics              │
│                                                             │
│  3. Build Feature (Sprint N)                                │
│     └── Implement tool (e.g., dasa profile)                 │
│                                                             │
│  4. Measure Improvement                                     │
│     └── Run eval WITH new tool → compare to baseline        │
│                                                             │
│  5. Repeat for each feature                                 │
│     └── Each tool should show improvement on relevant tasks │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Expected Improvement by Tool

| Tool | Improves | Task Categories |
|------|----------|-----------------|
| `dasa profile` | Data understanding, visualization | DU, VZ |
| `dasa check` | State recovery, dependency reasoning | SR, DR |
| `dasa run` | Bug fixing | BF |
| `dasa context` | All categories (persistent memory) | ALL |

---

## Eval Checkpoints

| Checkpoint | After Sprint | Expected Completion Rate |
|------------|--------------|------------------------|
| Baseline | 0 | ~43% (no DASA) |
| Eyes | 2 | ~56% (+13 pts) |
| MVP Complete | 3 | ~70% (+27 pts) |
| Multi-Agent | 4 | ~78% (+35 pts) |

---

## Success Metrics

| Metric | Target |
|--------|--------|
| MVP commands working | 4 (profile, check, run, context) |
| Test coverage | >80% |
| Install + first command | <30 seconds |
| Agent task success rate | +25% over baseline |
| First-attempt success | +30% over baseline |

---

## Documentation

| Document | Contents |
|----------|----------|
| [DESIGN.md](DESIGN.md) | Vision, problem, solution, multi-agent architecture |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Technical components, session system, package structure |
| [EVAL.md](EVAL.md) | Evaluation framework, task categories, metrics |
| [FORMAT.md](FORMAT.md) | Notebook format exploration (reference) |
| [sprints/](sprints/README.md) | Sprint details with code examples |

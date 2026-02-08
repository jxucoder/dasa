# AGENTS.md

Instructions for AI agents working on the DASA (Data Science Agent) project.

## Project Overview

DASA is an open source Data Science Agent toolkit that gives coding agents the specialized capabilities they need for notebook-based data science work. It solves three problems that make agents fail at notebooks: invisible data, inconsistent state, and context that evaporates between conversations.

### Four Commands

| Command | Purpose | What it does |
|---------|---------|-------------|
| `dasa profile` | **See the data** | Deep data profiling — columns, types, stats, quality issues. Auto-caches to `.dasa/profiles/`. |
| `dasa check` | **See notebook health** | Combined state validation + dependency graph + staleness detection in one report. |
| `dasa run` | **Execute safely** | Run cells with rich error context — available columns, "did you mean?", downstream warnings. |
| `dasa context` | **Remember across conversations** | Read/write persistent project memory — goal, status, approaches, decision log. |

### Key Concepts

- **Session (`.dasa/`)**: A directory that accumulates project knowledge. Tools auto-populate it — `profile` caches data profiles, `run` logs results, `check` records findings. Any agent reads `.dasa/context.yaml` to get full project state.
- **Agent Roles**: Profiler (read-only), Executor (can run cells), Analyst (read-only, strategic), Orchestrator (delegates). Defined in the agent skill.
- **Multi-agent coordination**: Agents coordinate through the shared `.dasa/` session, not through message passing. Same pattern as OpenCode's session hierarchy.

### Documentation

| Document | Contents |
|----------|----------|
| `docs/DESIGN.md` | Vision, problem, solution, multi-agent architecture |
| `docs/ARCHITECTURE.md` | Technical components, session system, package structure |
| `docs/PLAN.md` | Sprint roadmap (6 sprints, MVP = Sprints 0-3) |
| `docs/EVAL.md` | Evaluation framework, task categories, metrics |
| `docs/sprints/` | Sprint details with code examples |

## Python Environment

**Always use `uv` for Python package management.**

```bash
# Initial setup
uv venv
uv pip install -e ".[dev]"

# Common commands
uv add <package>           # Add dependency
uv add --dev <package>     # Add dev dependency
uv run <command>           # Run in venv
uv sync                    # Sync from pyproject.toml
```

## Code Style

- Use type hints for all function signatures
- Follow PEP 8 conventions
- Use `ruff` for linting and formatting
- Write docstrings for public functions and classes
- Prefer dataclasses for data structures
- All CLI output should support `--format json` for machine-readable output

## Project Structure

```
dasa/
├── src/dasa/               # Main package source
│   ├── cli/                # CLI commands (Typer)
│   │   ├── main.py         # Entry point
│   │   ├── profile.py      # dasa profile
│   │   ├── check.py        # dasa check
│   │   ├── run.py          # dasa run
│   │   └── context.py      # dasa context
│   ├── notebook/           # Notebook abstraction
│   │   ├── base.py         # Abstract adapter
│   │   ├── jupyter.py      # Jupyter .ipynb adapter
│   │   └── kernel.py       # Kernel manager
│   ├── analysis/           # Analysis engines
│   │   ├── parser.py       # AST variable extraction
│   │   ├── profiler.py     # Data profiling
│   │   ├── state.py        # State consistency
│   │   └── deps.py         # Dependency graph
│   ├── session/            # Session management (.dasa/)
│   │   ├── context.py      # context.yaml read/write
│   │   ├── profiles.py     # Profile cache
│   │   └── log.py          # Append-only log
│   └── output/             # Output formatting
│       └── formatter.py
├── skills/                 # Agent skills
│   └── notebook/
│       └── SKILL.md
├── eval/                   # Evaluation infrastructure (Sprint 0)
│   ├── notebooks/          # Test notebooks
│   ├── tasks/              # Task definitions
│   ├── harness/            # Eval runner, checker, metrics
│   └── results/
├── tests/                  # Unit tests
├── docs/                   # Documentation
│   ├── DESIGN.md           # Vision and architecture
│   ├── ARCHITECTURE.md     # Technical details
│   ├── PLAN.md             # Sprint roadmap
│   ├── EVAL.md             # Evaluation framework
│   └── sprints/            # Sprint details (00-05)
└── pyproject.toml
```

## Development Workflow

1. **Eval first**: Sprint 0 builds test infrastructure. Every feature should show measurable improvement.
2. **Session foundation**: Sprint 1 sets up `.dasa/` session. All subsequent tools build on it.
3. **4 commands, not 16**: Focus on `profile`, `check`, `run`, `context`. Don't build cell manipulation — agents can already edit JSON.
4. **Auto-populate session**: Every tool should automatically update `.dasa/` (cache profiles, log results). No manual maintenance.
5. **Reference sprint docs**: Detailed code examples for adapters, kernel, parser, profiler are in `docs/sprints/`. Use them as implementation reference.

## Sprint Overview

| Sprint | Name | Focus | Status |
|--------|------|-------|--------|
| **0** | Evaluation | Test notebooks, tasks, harness, baseline | |
| **1** | Core + Session | Package, `.dasa/` session, adapters, kernel, parser, skill | |
| **2** | Eyes | `dasa profile`, `dasa check` | |
| **3** | Hands + Memory | `dasa run`, `dasa context` | |
| **4** | Multi-Agent | Agent roles, auto-population hooks, background execution | |
| **5** | Extensions | MCP server, Marimo adapter, replay | |

**MVP = Sprints 0-3.** After MVP, eval should show >70% task completion with +25% improvement over baseline.

## Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=dasa

# Run specific test file
uv run pytest tests/test_cli/test_profile.py

# Run eval
cd eval && python -m harness.runner --output results/
```

## CLI Development

The CLI uses Typer. Each command is in its own module under `src/dasa/cli/`.

```bash
# Run during development
uv run dasa <command>

# After installing
dasa profile notebook.ipynb --var df
dasa check notebook.ipynb
dasa run notebook.ipynb --cell 3
dasa context
```

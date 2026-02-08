# DASA Architecture

Technical architecture for the Data Science Agent toolkit.

---

## System Overview

DASA is a CLI toolkit that gives coding agents specialized capabilities for notebook-based data science. It's not an agent platform — it's the tools that make agents good at data science.

```
┌─────────────────────────────────────────────────────────────┐
│                   Any Coding Agent                          │
│            (Cursor, Claude Code, OpenCode, etc.)            │
└──────────────────────────┬──────────────────────────────────┘
                           │
              ┌────────────▼────────────┐
              │     Agent Skill         │
              │     (SKILL.md)          │
              │                         │
              │  Teaches workflows:     │
              │  - Profile before code  │
              │  - Check before edit    │
              │  - Context at start     │
              └────────────┬────────────┘
                           │ runs via bash
              ┌────────────▼────────────┐
              │     DASA CLI            │
              │                         │
              │  dasa profile           │
              │  dasa check             │
              │  dasa run               │
              │  dasa context           │
              └────────────┬────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                  │
    ┌────▼─────┐    ┌──────▼──────┐    ┌─────▼──────┐
    │ Analysis │    │  Notebook   │    │  Session   │
    │ Engine   │    │  Layer      │    │  (.dasa/)  │
    │          │    │             │    │            │
    │ parser   │    │ adapter     │    │ context    │
    │ profiler │    │ kernel      │    │ profiles   │
    │ state    │    │             │    │ log        │
    │ deps     │    │             │    │            │
    └──────────┘    └─────────────┘    └────────────┘
```

---

## Core Components

### Notebook Adapter

Abstracts notebook formats behind a common interface.

```python
class NotebookAdapter(ABC):
    """Read/write/modify notebooks regardless of format."""
    
    def load(self, path: str) -> None: ...
    def save(self, path: str = None) -> None: ...
    
    @property
    def cells(self) -> list[Cell]: ...
    @property
    def code_cells(self) -> list[Cell]: ...
    @property
    def execution_order(self) -> list[int]: ...
    
    def get_cell(self, index: int) -> Cell: ...
    def add_cell(self, source: str, cell_type: str, index: int = None) -> Cell: ...
    def update_cell(self, index: int, source: str) -> None: ...
    def delete_cell(self, index: int) -> None: ...
```

**Implementations:**
- `JupyterAdapter` — reads/writes `.ipynb` via `nbformat` (Sprint 1)
- `MarimoAdapter` — parses `.py` files with `@app.cell` decorators (Sprint 5)

### Kernel Manager

Manages Jupyter kernel lifecycle and code execution.

```python
class KernelManager:
    """Start, execute, restart, interrupt Jupyter kernels."""
    
    def start(self) -> None: ...
    def shutdown(self) -> None: ...
    def restart(self) -> None: ...
    def interrupt(self) -> None: ...
    
    def execute(self, code: str, timeout: int = 300) -> ExecutionResult: ...
    def get_variable(self, var_name: str) -> Any: ...

@dataclass
class ExecutionResult:
    success: bool
    stdout: str
    stderr: str
    result: Optional[Any]
    error: Optional[str]
    error_type: Optional[str]
    traceback: Optional[list[str]]
    execution_time: float
```

### AST Parser

Extracts variable definitions and references from Python code using the `ast` module.

```python
def parse_cell(source: str) -> CellAnalysis:
    """Parse cell source and extract variable info."""

@dataclass
class CellAnalysis:
    definitions: set[str]   # Variables defined (assigned, imported)
    references: set[str]    # Variables referenced (used)
    imports: set[str]       # Imported names
    functions: set[str]     # Function definitions
    classes: set[str]       # Class definitions
```

Handles edge cases: magic commands (`%`), shell commands (`!`), tuple unpacking, walrus operator, comprehension scoping, star imports.

### Profiler

Generates data profiles by injecting profiling code into the kernel.

```python
class Profiler:
    """Profile variables in kernel memory."""
    
    def profile_dataframe(self, var_name: str) -> DataFrameProfile: ...
    def get_variable_type(self, var_name: str) -> str: ...

@dataclass
class DataFrameProfile:
    name: str
    shape: tuple[int, int]
    memory_bytes: int
    columns: list[ColumnProfile]
    issues: list[str]
    sample_rows: Optional[list[dict]]
```

Profile code is injected into the kernel and executed — the profiler sees the actual data, not just the code that created it.

### State Analyzer

Checks notebook state consistency by combining AST analysis with execution metadata.

```python
class StateAnalyzer:
    """Detect state inconsistencies in notebooks."""
    
    def analyze(self, adapter: NotebookAdapter) -> StateAnalysis: ...

@dataclass
class StateAnalysis:
    is_consistent: bool
    issues: list[StateIssue]         # Errors and warnings
    execution_order: list[int]       # Actual execution order
    correct_order: list[int]         # Expected order
    defined_vars: dict[str, int]     # var → defining cell
    undefined_refs: list[tuple[int, str]]  # (cell, var) with missing defs
```

Detects: undefined variables, out-of-order execution, stale outputs, never-executed cells.

### Dependency Analyzer

Builds a directed acyclic graph of cell dependencies.

```python
class DependencyAnalyzer:
    """Build and query cell dependency graph."""
    
    def build_graph(self, adapter: NotebookAdapter) -> DependencyGraph: ...

@dataclass
class DependencyGraph:
    nodes: dict[int, CellNode]
    
    def get_upstream(self, cell_index: int) -> list[int]: ...
    def get_downstream(self, cell_index: int) -> list[int]: ...

@dataclass
class CellNode:
    index: int
    definitions: set[str]
    references: set[str]
    upstream: set[int]    # Cells this depends on
    downstream: set[int]  # Cells that depend on this
```

---

## CLI Commands

Four commands, each solving a specific agent failure mode.

| Command | Purpose | Reads | Writes |
|---------|---------|-------|--------|
| `dasa profile` | See data structure | Kernel state | `.dasa/profiles/` |
| `dasa check` | See notebook health | Notebook file, AST | `.dasa/log` |
| `dasa run` | Execute cells safely | Notebook, kernel | `.dasa/log` |
| `dasa context` | Read/write project memory | `.dasa/context.yaml` | `.dasa/context.yaml`, `.dasa/log` |

All commands support `--format json` for machine-readable output.

### Command Flow

```
User/Agent calls dasa command
        │
        ▼
   Parse CLI args (Typer)
        │
        ▼
   Load notebook (JupyterAdapter)
        │
        ▼
   Execute core logic
   ├── profile: start kernel → inject profiling code → parse result
   ├── check: parse AST → analyze state → build dep graph → report
   ├── run: start kernel → execute cell → capture result → error context
   └── context: read/write .dasa/context.yaml
        │
        ▼
   Auto-update session (.dasa/)
   ├── profile → cache to .dasa/profiles/{var}.yaml
   ├── check → log issues to .dasa/log
   ├── run → log result to .dasa/log
   └── context → update .dasa/context.yaml
        │
        ▼
   Format output (text or JSON)
```

---

## Session System

The `.dasa/` directory is DASA's persistent memory. It accumulates knowledge across conversations, tools, and agents.

### Structure

```
.dasa/
├── context.yaml          # Project state: goal, status, approaches
├── profiles/             # Cached data profiles (auto-populated)
│   ├── df.yaml
│   └── clean_df.yaml
├── log                   # Append-only decision history
└── state.json            # Cell execution hashes (staleness tracking)
```

### Auto-Population

Tools automatically update the session. No manual maintenance needed.

| Tool | Auto-writes to |
|------|---------------|
| `dasa profile --var df` | `.dasa/profiles/df.yaml` |
| `dasa check notebook.ipynb` | `.dasa/log` (issues found) |
| `dasa run --cell 5` | `.dasa/log` (success/failure), `.dasa/state.json` (code hash) |
| `dasa context --log "..."` | `.dasa/log` |
| `dasa context --set-goal "..."` | `.dasa/context.yaml` |

### Staleness Tracking

`.dasa/state.json` tracks cell code hashes:

```json
{
  "notebook.ipynb": {
    "cells": {
      "0": {"code_hash": "abc123", "last_run": "2026-02-08T10:30:00"},
      "1": {"code_hash": "def456", "last_run": "2026-02-08T10:31:00"}
    }
  }
}
```

A cell is stale if: (1) current code hash differs from stored hash, OR (2) any upstream dependency is stale.

---

## Agent Skill System

The agent skill (`skills/notebook/SKILL.md`) teaches agents how and when to use DASA tools. It's the integration point between DASA and any coding agent platform.

### Skill Structure

```markdown
# Notebook Agent Skill

## When This Skill Applies
- Working with .ipynb files
- Data science or machine learning tasks

## Core Principles
1. Read context first — always start with `dasa context`
2. Profile before coding — see data before writing code that uses it
3. Check before editing — understand impact before modifying cells
4. Verify after changes — run affected cells to confirm

## Workflows
### Starting a Session
1. Run `dasa context` to get project state
2. If no context exists, ask user for goal

### Adding Code That Uses Data
1. Run `dasa profile notebook.ipynb --var df`
2. Note exact column names, types, issues
3. Write code using correct names
4. Run cell and verify

### Debugging Errors
1. Run `dasa run notebook.ipynb --cell N`
2. Read error context and suggestions
3. If data issue, profile the variable
4. Fix and re-run

### Before Modifying Cells
1. Run `dasa check notebook.ipynb`
2. Check dependencies for affected cells
3. Make changes
4. Run affected downstream cells
```

---

## Multi-Agent Coordination

DASA supports multi-agent workflows through shared session state, not through inter-agent messaging.

### Coordination via Session

```
Agent A (profiler)                    Agent B (executor)
    │                                      │
    ├── dasa profile --var df              │
    ├── writes .dasa/profiles/df.yaml      │
    ├── dasa context --log "profiled df"   │
    │                                      │
    │                                      ├── dasa context (reads state)
    │                                      ├── reads .dasa/profiles/df.yaml
    │                                      ├── writes code using correct columns
    │                                      ├── dasa run --cell 5
    │                                      └── dasa context --log "trained model"
```

### Agent Roles

Defined in the agent skill. Each role has clear boundaries:

```markdown
## Agent Roles

### Profiler (read-only, cheap model)
- Use: dasa profile, dasa check
- Cannot: execute cells, modify notebooks
- Model: fast/cheap (exploration work)

### Executor (can execute, cannot edit)
- Use: dasa run, dasa profile, dasa check
- Cannot: modify notebook source code
- Model: standard (needs to understand errors)

### Analyst (read-only, smart model)
- Use: dasa check, dasa context
- Cannot: execute or modify anything
- Model: smart/expensive (strategic reasoning)

### Orchestrator (delegates everything)
- Use: all tools via delegation to specialists
- Model: smartest (planning and coordination)
```

### Integration with Agent Platforms

DASA doesn't manage agents — it provides tools. The platform handles orchestration:

| Platform | How DASA Integrates |
|----------|-------------------|
| **OpenCode** | Task tool creates child session → child runs `dasa profile` → result returns to parent |
| **Cursor** | Agent skill teaches workflows → agent calls `dasa` via bash → reads `.dasa/` for context |
| **Claude Code** | AGENTS.md describes tools → agent calls `dasa` via bash → session persists across conversations |
| **MCP (future)** | Direct tool integration → agent calls profile/check/run as MCP tools |

---

## Future: MCP Server

Expose DASA tools via Model Context Protocol for direct agent integration:

```python
@server.tool("profile")
async def profile_tool(notebook: str, var: str) -> str:
    """Profile a variable. Returns column info, types, stats, issues."""
    ...

@server.tool("check")
async def check_tool(notebook: str) -> str:
    """Check notebook health. Returns state issues, deps, staleness."""
    ...

@server.tool("run")
async def run_tool(notebook: str, cell: int) -> str:
    """Execute a cell. Returns output or error with context."""
    ...

@server.tool("context")
async def context_tool(action: str = "read") -> str:
    """Read or update project context."""
    ...
```

Configuration:
```json
{
  "mcpServers": {
    "dasa": {
      "command": "dasa",
      "args": ["mcp-serve"]
    }
  }
}
```

---

## Package Structure

```
dasa/
├── src/dasa/
│   ├── __init__.py
│   ├── cli/                    # CLI commands (Typer)
│   │   ├── main.py             # App entry point
│   │   ├── profile.py          # dasa profile
│   │   ├── check.py            # dasa check (validate + deps + stale)
│   │   ├── run.py              # dasa run
│   │   └── context.py          # dasa context
│   ├── notebook/               # Notebook abstraction
│   │   ├── base.py             # Abstract adapter
│   │   ├── jupyter.py          # Jupyter .ipynb adapter
│   │   └── kernel.py           # Kernel manager
│   ├── analysis/               # Analysis engines
│   │   ├── parser.py           # AST variable extraction
│   │   ├── profiler.py         # Data profiling
│   │   ├── state.py            # State consistency checking
│   │   └── deps.py             # Dependency graph
│   ├── session/                # Session management
│   │   ├── context.py          # context.yaml read/write
│   │   ├── profiles.py         # Profile cache management
│   │   └── log.py              # Append-only log
│   └── output/                 # Output formatting
│       └── formatter.py        # Text/JSON formatting
├── skills/
│   └── notebook/
│       └── SKILL.md            # Agent skill
├── eval/                       # Evaluation infrastructure
├── tests/                      # Unit tests
└── pyproject.toml
```

---

## Dependencies

| Package | Purpose | Version |
|---------|---------|---------|
| `nbformat` | Read/write .ipynb files | >=5.9 |
| `nbclient` | Notebook execution | >=0.10 |
| `jupyter-client` | Kernel management | >=8.0 |
| `typer` | CLI framework | >=0.12 |
| `rich` | Terminal formatting | >=13.0 |
| `pyyaml` | YAML read/write for session | >=6.0 |

Dev dependencies: `pytest`, `ruff`, `mypy`

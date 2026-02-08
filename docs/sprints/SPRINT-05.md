# Sprint 5: Extensions

**Goal:** Add MCP server for direct agent integration, Marimo notebook support, and replay for reproducibility verification.

**Duration:** ~3-4 days

**Prerequisite:** Sprint 4 (Multi-Agent & Hooks)

---

## Deliverables

| # | Deliverable | Description |
|---|-------------|-------------|
| 1 | MCP server | Expose DASA tools via Model Context Protocol |
| 2 | Marimo adapter | Support for Marimo notebooks (.py) |
| 3 | `dasa replay` | Run notebook from scratch, verify reproducibility |

---

## Tasks

### 5.1 MCP Server

Expose DASA tools as MCP tools so agents can call them directly without going through bash.

```bash
# Start MCP server
dasa mcp-serve
```

**Configuration (for any MCP-compatible agent):**

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

#### `src/dasa/mcp/server.py`

```python
"""DASA MCP server."""

from mcp import Server

server = Server("dasa")


@server.tool("profile")
async def profile_tool(notebook: str, var: str) -> str:
    """Profile a variable in the notebook kernel.
    
    Returns column names, types, statistics, and data quality issues.
    Auto-caches the profile to .dasa/profiles/.
    """
    # Call profile logic directly (not via CLI)
    ...


@server.tool("check")
async def check_tool(notebook: str, cell: int = None) -> str:
    """Check notebook health: state, dependencies, staleness.
    
    If cell is provided, shows impact of modifying that cell.
    Returns state issues, dependency graph, and execution order.
    """
    ...


@server.tool("run")
async def run_tool(notebook: str, cell: int = None, all: bool = False) -> str:
    """Execute notebook cells with rich error context.
    
    Returns output or error with available columns/variables and suggestions.
    Auto-logs results to .dasa/log.
    """
    ...


@server.tool("context")
async def context_tool(
    action: str = "read",
    goal: str = None,
    status: str = None,
    log: str = None,
) -> str:
    """Read or update project context.
    
    action="read": Returns project state, data profiles, approaches, recent log.
    action="write": Updates goal, status, or appends to log.
    """
    ...
```

**Benefits over CLI:**
- No shell overhead — direct function calls
- Structured return types
- Better error handling
- Works in agent platforms that don't support bash (some MCP-only environments)

---

### 5.2 Marimo Adapter

Marimo notebooks are Python files with `@app.cell` decorators and explicit dependency declarations:

```python
import marimo

app = marimo.App()

@app.cell
def cell1():
    import pandas as pd
    df = pd.read_csv('data.csv')
    return df,

@app.cell
def cell2(df):  # Explicit dependency on df
    clean_df = df.dropna()
    return clean_df,
```

#### `src/dasa/notebook/marimo.py`

```python
"""Marimo notebook (.py) adapter."""

import ast
from pathlib import Path
from typing import Optional

from .base import Cell, NotebookAdapter


class MarimoAdapter(NotebookAdapter):
    """Adapter for Marimo .py notebooks."""
    
    def load(self, path: str) -> None:
        """Parse .py file and extract @app.cell functions."""
        self.path = Path(path)
        source = self.path.read_text()
        tree = ast.parse(source)
        
        self._cells = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if self._is_cell_function(node):
                    self._cells.append(self._parse_cell(node, source))
    
    def _is_cell_function(self, node: ast.FunctionDef) -> bool:
        """Check if function has @app.cell decorator."""
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Attribute):
                if decorator.attr == "cell":
                    return True
        return False
    
    def _parse_cell(self, node: ast.FunctionDef, source: str) -> Cell:
        """Extract cell info from function definition."""
        # Get function body source
        # Extract dependencies from function arguments
        # Extract returns from return statement
        ...
    
    @property
    def cells(self) -> list[Cell]:
        return self._cells
    
    # ... implement remaining abstract methods
```

**Marimo advantages for DASA:**
- Dependencies are explicit in function signatures (no AST guessing needed)
- No hidden state — each cell is a pure function
- `.py` files are easier to parse than `.ipynb` JSON

---

### 5.3 Replay Command

`dasa replay notebook.ipynb`

Run notebook from scratch in a fresh kernel and verify reproducibility.

```
$ dasa replay notebook.ipynb

Replaying from scratch (new kernel)...

Cell 0: ✓ (0.1s)
Cell 1: ✓ (0.5s) - outputs match
Cell 2: ✓ (0.3s) - outputs match
Cell 3: ⚠ (0.2s) - OUTPUT DIFFERS (random seed not set)
Cell 4: ✗ FAILED (0.1s) - FileNotFoundError: data/extra.csv

──────────────────────────────────────────────────
Total time: 1.2s
Cells executed: 4/5
Reproducibility Score: 60% (3/5 cells)

Issues Found:
  1. Cell 3: Output differs from original
     → Set random seed with np.random.seed(42)
  2. Cell 4: FileNotFoundError: data/extra.csv
     → Check if file exists and is committed to repo
```

**Key features:**
- Starts fresh kernel (no hidden state)
- Compares outputs to saved outputs (hash comparison)
- Calculates reproducibility score
- Suggests fixes for common issues

See `src/dasa/cli/replay.py` for the full implementation.

---

## Acceptance Criteria

- [ ] `dasa mcp-serve` starts MCP server
- [ ] MCP tools callable from any MCP-compatible agent
- [ ] `dasa profile marimo_notebook.py --var df` works with Marimo files
- [ ] `dasa check marimo_notebook.py` works with Marimo files
- [ ] `dasa replay notebook.ipynb` runs from scratch and reports reproducibility
- [ ] Replay suggests fixes for common issues
- [ ] All existing tests still pass

---

## Files Created

```
src/dasa/
├── cli/
│   ├── mcp_serve.py        # NEW: MCP server command
│   └── replay.py           # NEW: replay command
├── mcp/
│   ├── __init__.py          # NEW
│   └── server.py            # NEW: MCP server implementation
└── notebook/
    └── marimo.py            # NEW: Marimo adapter
```

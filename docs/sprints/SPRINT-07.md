# Sprint 7: Extensions (Stretch)

**Goal:** Add Marimo support, MCP server, and enhanced output descriptions.

**Duration:** ~3-4 days

**Prerequisite:** Sprint 6 (Info tools & async)

---

## Deliverables

| # | Deliverable | Description |
|---|-------------|-------------|
| 1 | Marimo adapter | Support for Marimo notebooks (.py) |
| 2 | MCP server | Model Context Protocol server |
| 3 | Rich outputs | Enhanced output descriptions |

---

## Tasks

### 7.1 Marimo Adapter

Marimo notebooks are Python files with `@app.cell` decorators:

```python
import marimo

app = marimo.App()

@app.cell
def cell1():
    import pandas as pd
    df = pd.read_csv('data.csv')
    return df,

@app.cell
def cell2(df):
    clean_df = df.dropna()
    return clean_df,
```

**Adapter features:**
- Parse `.py` files with Marimo decorators
- Extract cells as functions
- Infer dependencies from function signatures
- Execute via Marimo runtime

---

### 7.2 MCP Server

Expose DASA tools via Model Context Protocol:

```python
# dasa/mcp/server.py
from mcp import Server

server = Server("dasa")

@server.tool("profile")
async def profile_tool(notebook: str, var: str):
    """Profile a variable in the notebook."""
    # Call profile logic
    pass

@server.tool("validate")
async def validate_tool(notebook: str):
    """Validate notebook state."""
    pass
```

**Usage:**
```bash
dasa mcp-serve
```

**Configuration:**
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

### 7.3 Rich Output Descriptions

Enhanced output analysis using heuristics:

**For matplotlib figures:**
- Detect chart type (bar, line, scatter, etc.)
- Extract axis labels and title
- Count data points/bars
- Identify trends

**For DataFrames:**
- Shape and column summary
- First/last rows preview

**For images:**
- Dimensions and format
- Basic color analysis

**Future (Vision API):**
- Full image understanding
- Complex chart analysis
- Diagram comprehension

---

## Acceptance Criteria

- [ ] `dasa profile marimo_notebook.py --var df` works
- [ ] `dasa validate marimo_notebook.py` works
- [ ] `dasa mcp-serve` starts MCP server
- [ ] MCP tools callable from Cursor/Claude
- [ ] Output descriptions include chart details

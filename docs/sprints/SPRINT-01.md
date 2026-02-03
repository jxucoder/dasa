# Sprint 1: Project Setup & Core Infrastructure

**Goal:** Create installable package with core infrastructure (notebook adapter, kernel manager, AST parser).

**Duration:** ~2-3 days

**Prerequisite:** Sprint 0 (Eval infrastructure)

---

## Deliverables

| # | Deliverable | Description |
|---|-------------|-------------|
| 1 | Package skeleton | pyproject.toml, src layout, installable via pip |
| 2 | Agent skill | SKILL.md teaching agents notebook best practices |
| 3 | Jupyter adapter | Read/write/modify .ipynb files |
| 4 | Kernel manager | Start/execute/restart Jupyter kernels |
| 5 | AST parser | Extract variable defs/refs from Python code |
| 6 | Output formatter | LLM-friendly formatting utilities |

---

## Tasks

### 1.1 Project Setup

#### `pyproject.toml`

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "dasa"
version = "0.1.0"
description = "Data Science Agent toolkit for notebook-based workflows"
readme = "README.md"
license = "Apache-2.0"
requires-python = ">=3.10"
authors = [
    { name = "DASA Team" }
]
keywords = ["jupyter", "notebook", "data-science", "agent", "llm"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: Apache Software License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]

dependencies = [
    "nbformat>=5.9",
    "nbclient>=0.10",
    "jupyter-client>=8.0",
    "typer>=0.12",
    "rich>=13.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
    "black>=24.0",
    "ruff>=0.1",
    "mypy>=1.0",
]

[project.scripts]
dasa = "dasa.cli.main:app"

[tool.hatch.build.targets.wheel]
packages = ["src/dasa"]

[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W"]

[tool.mypy]
python_version = "3.10"
strict = true

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

#### Directory Structure

```
mkdir -p src/dasa/{cli,notebook,analysis,output}
touch src/dasa/__init__.py
touch src/dasa/cli/__init__.py
touch src/dasa/notebook/__init__.py
touch src/dasa/analysis/__init__.py
touch src/dasa/output/__init__.py
```

---

### 1.2 Agent Skill

Create `skills/notebook/SKILL.md`:

```markdown
# Notebook Agent Skill

This skill teaches you how to work effectively with Jupyter notebooks using DASA tools.

## When This Skill Applies

- Working with `.ipynb` files
- Data science or machine learning tasks
- Tasks involving pandas DataFrames, numpy arrays, or visualizations

## Core Principles

1. **Profile before coding** - Always understand your data before writing code that uses it
2. **Validate state** - Check notebook consistency when things seem wrong
3. **Check dependencies** - Understand impact before modifying cells
4. **Verify reproducibility** - Ensure notebooks work from scratch

## Available Tools

### Understanding Tools

```bash
# Profile a variable to understand its structure
dasa profile notebook.ipynb --var df

# Check notebook state for issues
dasa validate notebook.ipynb

# See cell dependencies
dasa deps notebook.ipynb
dasa deps notebook.ipynb --cell 3  # Impact of changing cell 3
```

### Execution Tools

```bash
# Run a specific cell
dasa run notebook.ipynb --cell 3

# Verify reproducibility
dasa replay notebook.ipynb
```

## Workflows

### Adding Code That Uses Data

1. First, profile the data:
   ```bash
   dasa profile notebook.ipynb --var df
   ```
2. Note the exact column names, types, and any data quality issues
3. Write code using the correct column names
4. Run and verify

### Debugging Errors

1. Run the failing cell to see the error:
   ```bash
   dasa run notebook.ipynb --cell 5
   ```
2. Check the error context and suggestions
3. If it's a data issue, profile the relevant variable
4. Fix and re-run

### Fixing Inconsistent State

1. Validate the notebook:
   ```bash
   dasa validate notebook.ipynb
   ```
2. Review the issues (stale outputs, undefined variables, etc.)
3. Either fix individual cells or replay from scratch:
   ```bash
   dasa replay notebook.ipynb
   ```

### Modifying Cells

1. Check what depends on the cell:
   ```bash
   dasa deps notebook.ipynb --cell 2
   ```
2. Make your changes
3. Re-run affected cells

## Common Mistakes to Avoid

- **Don't assume column names** - Always profile first
- **Don't ignore state warnings** - They indicate real problems
- **Don't modify cells without checking deps** - You'll break downstream cells
- **Don't trust stale outputs** - Re-run to verify
```

---

### 1.3 Jupyter Adapter

#### `src/dasa/notebook/base.py`

```python
"""Abstract notebook adapter interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Cell:
    """Represents a notebook cell."""
    index: int
    cell_type: str  # "code", "markdown", "raw"
    source: str
    outputs: list[dict] = field(default_factory=list)
    execution_count: Optional[int] = None
    metadata: dict = field(default_factory=dict)
    
    @property
    def is_code(self) -> bool:
        return self.cell_type == "code"
    
    @property
    def preview(self) -> str:
        """First line of source, truncated."""
        first_line = self.source.split('\n')[0]
        return first_line[:50] + ('...' if len(first_line) > 50 else '')


class NotebookAdapter(ABC):
    """Abstract interface for notebook formats."""
    
    @abstractmethod
    def load(self, path: str) -> None:
        """Load notebook from file."""
        pass
    
    @abstractmethod
    def save(self, path: Optional[str] = None) -> None:
        """Save notebook to file."""
        pass
    
    @property
    @abstractmethod
    def cells(self) -> list[Cell]:
        """Get all cells."""
        pass
    
    @property
    def code_cells(self) -> list[Cell]:
        """Get only code cells."""
        return [c for c in self.cells if c.is_code]
    
    @abstractmethod
    def add_cell(
        self,
        source: str,
        cell_type: str = "code",
        index: Optional[int] = None
    ) -> Cell:
        """Add a new cell."""
        pass
    
    @abstractmethod
    def update_cell(self, index: int, source: str) -> None:
        """Update cell source."""
        pass
    
    @abstractmethod
    def delete_cell(self, index: int) -> None:
        """Delete a cell."""
        pass
    
    @abstractmethod
    def get_cell(self, index: int) -> Cell:
        """Get cell by index."""
        pass
```

#### `src/dasa/notebook/jupyter.py`

```python
"""Jupyter notebook (.ipynb) adapter."""

from pathlib import Path
from typing import Optional

import nbformat
from nbformat import NotebookNode

from .base import Cell, NotebookAdapter


class JupyterAdapter(NotebookAdapter):
    """Adapter for Jupyter .ipynb notebooks."""
    
    def __init__(self, path: Optional[str] = None):
        self.path: Optional[Path] = None
        self._notebook: Optional[NotebookNode] = None
        
        if path:
            self.load(path)
    
    def load(self, path: str) -> None:
        """Load notebook from .ipynb file."""
        self.path = Path(path)
        with open(self.path) as f:
            self._notebook = nbformat.read(f, as_version=4)
    
    def save(self, path: Optional[str] = None) -> None:
        """Save notebook to file."""
        save_path = Path(path) if path else self.path
        if not save_path:
            raise ValueError("No path specified")
        
        with open(save_path, 'w') as f:
            nbformat.write(self._notebook, f)
    
    @property
    def cells(self) -> list[Cell]:
        """Get all cells as Cell objects."""
        if not self._notebook:
            return []
        
        return [
            Cell(
                index=i,
                cell_type=c.cell_type,
                source=c.source,
                outputs=getattr(c, 'outputs', []),
                execution_count=getattr(c, 'execution_count', None),
                metadata=dict(c.metadata)
            )
            for i, c in enumerate(self._notebook.cells)
        ]
    
    def get_cell(self, index: int) -> Cell:
        """Get cell by index."""
        cells = self.cells
        if index < 0 or index >= len(cells):
            raise IndexError(f"Cell index {index} out of range")
        return cells[index]
    
    def add_cell(
        self,
        source: str,
        cell_type: str = "code",
        index: Optional[int] = None
    ) -> Cell:
        """Add a new cell at the specified index."""
        if not self._notebook:
            raise ValueError("No notebook loaded")
        
        if cell_type == "code":
            new_cell = nbformat.v4.new_code_cell(source)
        elif cell_type == "markdown":
            new_cell = nbformat.v4.new_markdown_cell(source)
        else:
            new_cell = nbformat.v4.new_raw_cell(source)
        
        if index is None:
            index = len(self._notebook.cells)
        
        self._notebook.cells.insert(index, new_cell)
        
        return Cell(
            index=index,
            cell_type=cell_type,
            source=source,
            outputs=[],
            execution_count=None,
            metadata={}
        )
    
    def update_cell(self, index: int, source: str) -> None:
        """Update cell source code."""
        if not self._notebook:
            raise ValueError("No notebook loaded")
        
        if index < 0 or index >= len(self._notebook.cells):
            raise IndexError(f"Cell index {index} out of range")
        
        self._notebook.cells[index].source = source
    
    def delete_cell(self, index: int) -> None:
        """Delete cell at index."""
        if not self._notebook:
            raise ValueError("No notebook loaded")
        
        if index < 0 or index >= len(self._notebook.cells):
            raise IndexError(f"Cell index {index} out of range")
        
        del self._notebook.cells[index]
    
    @property
    def execution_order(self) -> list[int]:
        """Get actual execution order from execution counts."""
        cells_with_count = [
            (i, c.execution_count)
            for i, c in enumerate(self._notebook.cells)
            if c.cell_type == "code" and c.execution_count is not None
        ]
        
        # Sort by execution count to get order
        sorted_cells = sorted(cells_with_count, key=lambda x: x[1])
        return [i for i, _ in sorted_cells]
    
    @property 
    def kernel_spec(self) -> Optional[str]:
        """Get kernel specification name."""
        if not self._notebook:
            return None
        return self._notebook.metadata.get('kernelspec', {}).get('name')
```

---

### 1.4 Kernel Manager

#### `src/dasa/notebook/kernel.py`

```python
"""Jupyter kernel management."""

import queue
from dataclasses import dataclass
from typing import Any, Optional

from jupyter_client import KernelManager as JupyterKernelManager


@dataclass
class ExecutionResult:
    """Result of code execution."""
    success: bool
    stdout: str
    stderr: str
    result: Optional[Any]
    error: Optional[str] = None
    error_type: Optional[str] = None
    traceback: Optional[list[str]] = None
    execution_time: float = 0.0


class KernelManager:
    """Manages Jupyter kernel for code execution."""
    
    def __init__(self, kernel_name: str = "python3"):
        self.kernel_name = kernel_name
        self._km: Optional[JupyterKernelManager] = None
        self._kc = None  # KernelClient
    
    @property
    def is_alive(self) -> bool:
        """Check if kernel is running."""
        return self._km is not None and self._km.is_alive()
    
    def start(self) -> None:
        """Start the kernel."""
        if self.is_alive:
            return
        
        self._km = JupyterKernelManager(kernel_name=self.kernel_name)
        self._km.start_kernel()
        self._kc = self._km.client()
        self._kc.start_channels()
        self._kc.wait_for_ready(timeout=60)
    
    def shutdown(self) -> None:
        """Shutdown the kernel."""
        if self._kc:
            self._kc.stop_channels()
        if self._km:
            self._km.shutdown_kernel(now=True)
        self._km = None
        self._kc = None
    
    def restart(self) -> None:
        """Restart the kernel (clears all state)."""
        if self._km:
            self._km.restart_kernel(now=True)
            self._kc.wait_for_ready(timeout=60)
        else:
            self.start()
    
    def interrupt(self) -> None:
        """Interrupt current execution."""
        if self._km:
            self._km.interrupt_kernel()
    
    def execute(self, code: str, timeout: int = 300) -> ExecutionResult:
        """Execute code and return result."""
        if not self._kc:
            self.start()
        
        msg_id = self._kc.execute(code)
        
        stdout_parts: list[str] = []
        stderr_parts: list[str] = []
        result = None
        error = None
        error_type = None
        traceback = None
        
        while True:
            try:
                msg = self._kc.get_iopub_msg(timeout=timeout)
            except queue.Empty:
                return ExecutionResult(
                    success=False,
                    stdout="".join(stdout_parts),
                    stderr="".join(stderr_parts),
                    result=None,
                    error="Execution timed out",
                    error_type="TimeoutError"
                )
            
            # Skip messages from other executions
            if msg['parent_header'].get('msg_id') != msg_id:
                continue
            
            msg_type = msg['msg_type']
            content = msg['content']
            
            if msg_type == 'stream':
                if content['name'] == 'stdout':
                    stdout_parts.append(content['text'])
                elif content['name'] == 'stderr':
                    stderr_parts.append(content['text'])
            
            elif msg_type == 'execute_result':
                result = content.get('data', {})
            
            elif msg_type == 'display_data':
                # Could capture displays here
                pass
            
            elif msg_type == 'error':
                error_type = content['ename']
                error = content['evalue']
                traceback = content['traceback']
            
            elif msg_type == 'status':
                if content['execution_state'] == 'idle':
                    break
        
        return ExecutionResult(
            success=error is None,
            stdout="".join(stdout_parts),
            stderr="".join(stderr_parts),
            result=result,
            error=error,
            error_type=error_type,
            traceback=traceback
        )
    
    def get_variable(self, var_name: str) -> Any:
        """Get a variable's value from the kernel."""
        code = f"__dasa_result__ = {var_name}"
        result = self.execute(code)
        
        if not result.success:
            raise NameError(f"Variable '{var_name}' not found: {result.error}")
        
        # Get the value as JSON for transfer
        code = f"""
import json
try:
    print(json.dumps(__dasa_result__, default=str))
except:
    print(repr(__dasa_result__))
"""
        result = self.execute(code)
        return result.stdout.strip()
```

---

### 1.5 AST Parser

#### `src/dasa/analysis/parser.py`

```python
"""Python AST parsing for variable extraction."""

import ast
from dataclasses import dataclass, field


@dataclass
class CellAnalysis:
    """Analysis results for a code cell."""
    definitions: set[str] = field(default_factory=set)
    references: set[str] = field(default_factory=set)
    imports: set[str] = field(default_factory=set)
    functions: set[str] = field(default_factory=set)
    classes: set[str] = field(default_factory=set)


class VariableVisitor(ast.NodeVisitor):
    """AST visitor to extract variable definitions and references."""
    
    def __init__(self):
        self.definitions: set[str] = set()
        self.references: set[str] = set()
        self.imports: set[str] = set()
        self.functions: set[str] = set()
        self.classes: set[str] = set()
        self._scope_stack: list[set[str]] = [set()]
    
    def visit_Name(self, node: ast.Name) -> None:
        """Visit a Name node (variable reference or assignment target)."""
        if isinstance(node.ctx, ast.Store):
            self.definitions.add(node.id)
            self._scope_stack[-1].add(node.id)
        elif isinstance(node.ctx, ast.Load):
            # Only count as reference if not defined in current scope
            if node.id not in self._scope_stack[-1]:
                self.references.add(node.id)
        self.generic_visit(node)
    
    def visit_Import(self, node: ast.Import) -> None:
        """Visit import statement."""
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name.split('.')[0]
            self.imports.add(name)
            self.definitions.add(name)
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Visit from ... import statement."""
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            if name == '*':
                continue  # Can't track star imports
            self.imports.add(name)
            self.definitions.add(name)
        self.generic_visit(node)
    
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definition."""
        self.functions.add(node.name)
        self.definitions.add(node.name)
        
        # Enter new scope for function body
        self._scope_stack.append(set())
        
        # Add parameters to local scope
        for arg in node.args.args:
            self._scope_stack[-1].add(arg.arg)
        
        self.generic_visit(node)
        self._scope_stack.pop()
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function definition."""
        self.functions.add(node.name)
        self.definitions.add(node.name)
        
        self._scope_stack.append(set())
        for arg in node.args.args:
            self._scope_stack[-1].add(arg.arg)
        self.generic_visit(node)
        self._scope_stack.pop()
    
    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definition."""
        self.classes.add(node.name)
        self.definitions.add(node.name)
        
        self._scope_stack.append(set())
        self.generic_visit(node)
        self._scope_stack.pop()
    
    def visit_For(self, node: ast.For) -> None:
        """Visit for loop (loop variable is defined)."""
        self._visit_target(node.target)
        self.generic_visit(node)
    
    def visit_comprehension(self, node: ast.comprehension) -> None:
        """Visit comprehension (loop variable is local)."""
        # Comprehension variables should be local
        self._scope_stack.append(set())
        self._visit_target(node.target)
        self.generic_visit(node)
        self._scope_stack.pop()
    
    def visit_NamedExpr(self, node: ast.NamedExpr) -> None:
        """Visit walrus operator (:=)."""
        self.definitions.add(node.target.id)
        self.generic_visit(node)
    
    def _visit_target(self, target: ast.AST) -> None:
        """Extract names from assignment target."""
        if isinstance(target, ast.Name):
            self.definitions.add(target.id)
            self._scope_stack[-1].add(target.id)
        elif isinstance(target, (ast.Tuple, ast.List)):
            for elt in target.elts:
                self._visit_target(elt)


def parse_cell(source: str) -> CellAnalysis:
    """Parse a cell's source code and extract variable info."""
    
    # Skip magic commands and shell commands
    lines = []
    for line in source.split('\n'):
        stripped = line.strip()
        if stripped.startswith('%') or stripped.startswith('!'):
            continue
        lines.append(line)
    
    clean_source = '\n'.join(lines)
    
    try:
        tree = ast.parse(clean_source)
    except SyntaxError:
        # If we can't parse, return empty analysis
        return CellAnalysis()
    
    visitor = VariableVisitor()
    visitor.visit(tree)
    
    # Remove builtins from references
    builtins = set(dir(__builtins__)) if isinstance(__builtins__, dict) else set(dir(__builtins__))
    references = visitor.references - builtins - visitor.definitions
    
    return CellAnalysis(
        definitions=visitor.definitions,
        references=references,
        imports=visitor.imports,
        functions=visitor.functions,
        classes=visitor.classes
    )
```

---

### 1.6 Output Formatter

#### `src/dasa/output/formatter.py`

```python
"""LLM-friendly output formatting."""

from typing import Any, Optional


def format_bytes(size: int) -> str:
    """Format byte size for display."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def format_error(
    error_type: str,
    error_msg: str,
    line_number: Optional[int] = None,
    line_content: Optional[str] = None,
    suggestion: Optional[str] = None,
    available: Optional[list[str]] = None
) -> str:
    """Format an error with helpful context."""
    
    lines = [f"Error: {error_type}: {error_msg}"]
    
    if line_number and line_content:
        lines.append("")
        lines.append(f"Line {line_number}: {line_content}")
    
    if available:
        lines.append("")
        lines.append(f"Available: {', '.join(available)}")
    
    if suggestion:
        lines.append("")
        lines.append(f"Suggestion: {suggestion}")
    
    return "\n".join(lines)


def format_cell_header(index: int, cell_type: str, preview: str) -> str:
    """Format a cell header."""
    return f"[{index}] {cell_type}: {preview}"


def format_execution_result(
    cell_index: int,
    success: bool,
    elapsed: float,
    stdout: str = "",
    stderr: str = "",
    error: Optional[str] = None
) -> str:
    """Format execution result."""
    
    status = "✓" if success else "✗"
    lines = [f"Cell {cell_index}: {status} ({elapsed:.2f}s)"]
    
    if stdout:
        lines.append("")
        lines.append("Output:")
        for line in stdout.strip().split('\n')[:10]:  # Limit output
            lines.append(f"  {line}")
        if stdout.count('\n') > 10:
            lines.append("  ... (truncated)")
    
    if stderr:
        lines.append("")
        lines.append("Stderr:")
        for line in stderr.strip().split('\n')[:5]:
            lines.append(f"  {line}")
    
    if error:
        lines.append("")
        lines.append(f"Error: {error}")
    
    return "\n".join(lines)


def format_table(headers: list[str], rows: list[list[Any]]) -> str:
    """Format data as a simple text table."""
    
    # Calculate column widths
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))
    
    # Build table
    lines = []
    
    # Header
    header_line = "  ".join(
        str(h).ljust(widths[i]) for i, h in enumerate(headers)
    )
    lines.append(header_line)
    lines.append("-" * len(header_line))
    
    # Rows
    for row in rows:
        row_line = "  ".join(
            str(cell).ljust(widths[i]) for i, cell in enumerate(row)
        )
        lines.append(row_line)
    
    return "\n".join(lines)
```

---

### 1.7 CLI Entry Point

#### `src/dasa/cli/main.py`

```python
"""DASA CLI entry point."""

import typer
from rich.console import Console

app = typer.Typer(
    name="dasa",
    help="Data Science Agent toolkit for notebooks",
    no_args_is_help=True
)

console = Console()


@app.command()
def version():
    """Show DASA version."""
    from dasa import __version__
    console.print(f"dasa {__version__}")


# Commands will be added in subsequent sprints:
# - profile (Sprint 2)
# - validate (Sprint 2)
# - deps (Sprint 2)
# - run (Sprint 3)
# - replay (Sprint 3)


if __name__ == "__main__":
    app()
```

#### `src/dasa/__init__.py`

```python
"""DASA: Data Science Agent toolkit."""

__version__ = "0.1.0"

from pathlib import Path

# Path to the agent skill file
SKILL_PATH = Path(__file__).parent.parent.parent / "skills" / "notebook" / "SKILL.md"
```

---

## Acceptance Criteria

- [ ] Package installs with `pip install -e .`
- [ ] `dasa version` command works
- [ ] Jupyter adapter can load/save/modify notebooks
- [ ] Kernel manager can execute code
- [ ] AST parser extracts definitions and references
- [ ] All unit tests pass

---

## Tests

```python
# tests/test_notebook/test_jupyter.py
def test_load_notebook(clean_notebook):
    adapter = JupyterAdapter(clean_notebook)
    assert len(adapter.cells) == 6
    assert adapter.cells[0].is_code

def test_update_cell(clean_notebook):
    adapter = JupyterAdapter(clean_notebook)
    adapter.update_cell(0, "# modified")
    assert adapter.cells[0].source == "# modified"

# tests/test_analysis/test_parser.py
def test_parse_simple_assignment():
    analysis = parse_cell("x = 1")
    assert "x" in analysis.definitions
    assert len(analysis.references) == 0

def test_parse_references():
    analysis = parse_cell("y = x + 1")
    assert "y" in analysis.definitions
    assert "x" in analysis.references
```

---

## Files Created

```
src/
└── dasa/
    ├── __init__.py
    ├── cli/
    │   ├── __init__.py
    │   └── main.py
    ├── notebook/
    │   ├── __init__.py
    │   ├── base.py
    │   ├── jupyter.py
    │   └── kernel.py
    ├── analysis/
    │   ├── __init__.py
    │   └── parser.py
    └── output/
        ├── __init__.py
        └── formatter.py
skills/
└── notebook/
    └── SKILL.md
pyproject.toml
```

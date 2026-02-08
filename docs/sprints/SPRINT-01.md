# Sprint 1: Core + Session Foundation

**Goal:** Create installable package with core infrastructure (session system, notebook adapter, kernel manager, AST parser) and agent skill.

**Duration:** ~3-4 days

**Prerequisite:** Sprint 0 (Eval infrastructure)

---

## Deliverables

| # | Deliverable | Description |
|---|-------------|-------------|
| 1 | Package skeleton | pyproject.toml, src layout, installable via pip |
| 2 | Session system | `.dasa/` directory with context.yaml, profiles/, log |
| 3 | Agent skill | SKILL.md teaching agents notebook best practices |
| 4 | Jupyter adapter | Read/write/modify .ipynb files |
| 5 | Kernel manager | Start/execute/restart Jupyter kernels |
| 6 | AST parser | Extract variable defs/refs from Python code |
| 7 | Output formatter | LLM-friendly formatting utilities |

---

## Tasks

### 1.1 Project Setup

#### pyproject.toml

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
dependencies = [
    "nbformat>=5.9",
    "nbclient>=0.10",
    "jupyter-client>=8.0",
    "typer>=0.12",
    "rich>=13.0",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "ruff>=0.1",
    "mypy>=1.0",
]

[project.scripts]
dasa = "dasa.cli.main:app"

[tool.hatch.build.targets.wheel]
packages = ["src/dasa"]
```

---

### 1.2 Session System

The session is the foundation. Every subsequent tool reads from and writes to it.

#### `src/dasa/session/context.py`

```python
"""Project context management (.dasa/context.yaml)."""

from pathlib import Path
from typing import Optional
import yaml
from dataclasses import dataclass, field


@dataclass
class ProjectContext:
    """Project-level context persisted in .dasa/context.yaml."""
    name: Optional[str] = None
    goal: Optional[str] = None
    status: Optional[str] = None
    notebook: Optional[str] = None
    constraints: list[str] = field(default_factory=list)
    approaches: list[dict] = field(default_factory=list)
    data: dict = field(default_factory=dict)


class ContextManager:
    """Read/write .dasa/context.yaml."""
    
    def __init__(self, project_dir: str = "."):
        self.project_dir = Path(project_dir)
        self.dasa_dir = self.project_dir / ".dasa"
        self.context_path = self.dasa_dir / "context.yaml"
    
    def ensure_session(self) -> None:
        """Create .dasa/ directory structure if it doesn't exist."""
        self.dasa_dir.mkdir(exist_ok=True)
        (self.dasa_dir / "profiles").mkdir(exist_ok=True)
        if not (self.dasa_dir / "log").exists():
            (self.dasa_dir / "log").touch()
    
    def read(self) -> ProjectContext:
        """Read project context."""
        if not self.context_path.exists():
            return ProjectContext()
        
        with open(self.context_path) as f:
            data = yaml.safe_load(f) or {}
        
        project = data.get("project", {})
        return ProjectContext(
            name=project.get("name"),
            goal=project.get("goal"),
            status=project.get("status"),
            notebook=project.get("notebook"),
            constraints=project.get("constraints", []),
            approaches=data.get("approaches", []),
            data=data.get("data", {}),
        )
    
    def write(self, context: ProjectContext) -> None:
        """Write project context."""
        self.ensure_session()
        
        data = {
            "project": {
                "name": context.name,
                "goal": context.goal,
                "status": context.status,
                "notebook": context.notebook,
                "constraints": context.constraints,
            },
            "approaches": context.approaches,
            "data": context.data,
        }
        
        # Remove None values
        data["project"] = {k: v for k, v in data["project"].items() if v is not None}
        
        with open(self.context_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
    
    def update(self, **kwargs) -> ProjectContext:
        """Update specific fields in context."""
        context = self.read()
        for key, value in kwargs.items():
            if hasattr(context, key) and value is not None:
                setattr(context, key, value)
        self.write(context)
        return context
```

#### `src/dasa/session/log.py`

```python
"""Append-only decision log (.dasa/log)."""

from pathlib import Path
from datetime import datetime


class SessionLog:
    """Append-only log of decisions and actions."""
    
    def __init__(self, project_dir: str = "."):
        self.log_path = Path(project_dir) / ".dasa" / "log"
    
    def append(self, source: str, message: str) -> None:
        """Append an entry to the log."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        entry = f"{timestamp} [{source}] {message}\n"
        
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.log_path, "a") as f:
            f.write(entry)
    
    def read(self, last_n: int = 20) -> list[str]:
        """Read recent log entries."""
        if not self.log_path.exists():
            return []
        
        with open(self.log_path) as f:
            lines = f.readlines()
        
        return [line.strip() for line in lines[-last_n:]]
    
    def read_all(self) -> str:
        """Read entire log."""
        if not self.log_path.exists():
            return ""
        return self.log_path.read_text()
```

#### `src/dasa/session/profiles.py`

```python
"""Cached data profiles (.dasa/profiles/)."""

from pathlib import Path
from typing import Optional
import yaml


class ProfileCache:
    """Cache and retrieve data profiles."""
    
    def __init__(self, project_dir: str = "."):
        self.profiles_dir = Path(project_dir) / ".dasa" / "profiles"
    
    def save(self, var_name: str, profile: dict) -> Path:
        """Save a profile to cache."""
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        path = self.profiles_dir / f"{var_name}.yaml"
        
        with open(path, "w") as f:
            yaml.dump(profile, f, default_flow_style=False, sort_keys=False)
        
        return path
    
    def load(self, var_name: str) -> Optional[dict]:
        """Load a cached profile."""
        path = self.profiles_dir / f"{var_name}.yaml"
        if not path.exists():
            return None
        
        with open(path) as f:
            return yaml.safe_load(f)
    
    def list_profiles(self) -> list[str]:
        """List all cached profile names."""
        if not self.profiles_dir.exists():
            return []
        return [p.stem for p in self.profiles_dir.glob("*.yaml")]
```

---

### 1.3 Agent Skill

Create `skills/notebook/SKILL.md` — see [ARCHITECTURE.md](../ARCHITECTURE.md#agent-skill-system) for the full skill structure.

Key workflows the skill teaches:
1. **Starting a session:** Run `dasa context` first
2. **Before writing data code:** Run `dasa profile` to see columns/types
3. **Before modifying cells:** Run `dasa check` to understand dependencies
4. **Debugging errors:** Run `dasa run --cell N` for rich error context
5. **End of session:** Run `dasa context --log` to record progress

---

### 1.4 Jupyter Adapter

See `legacy_docs/sprints/SPRINT-01.md` for full implementation. Key classes:

- `NotebookAdapter` (abstract base) — `load`, `save`, `cells`, `get_cell`, `add_cell`, `update_cell`, `delete_cell`
- `JupyterAdapter` — concrete implementation using `nbformat`
- `Cell` dataclass — `index`, `cell_type`, `source`, `outputs`, `execution_count`

---

### 1.5 Kernel Manager

See `legacy_docs/sprints/SPRINT-01.md` for full implementation. Key class:

- `KernelManager` — `start`, `shutdown`, `restart`, `interrupt`, `execute(code) -> ExecutionResult`
- `ExecutionResult` — `success`, `stdout`, `stderr`, `result`, `error`, `error_type`, `traceback`

---

### 1.6 AST Parser

See `legacy_docs/sprints/SPRINT-01.md` for full implementation. Key function:

- `parse_cell(source) -> CellAnalysis` — extracts definitions, references, imports, functions, classes

---

### 1.7 CLI Entry Point

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


# Commands added in subsequent sprints:
# - profile (Sprint 2)
# - check (Sprint 2)
# - run (Sprint 3)
# - context (Sprint 3)


if __name__ == "__main__":
    app()
```

---

## Acceptance Criteria

- [ ] Package installs with `pip install -e .`
- [ ] `dasa version` command works
- [ ] `.dasa/` directory can be created and managed
- [ ] `context.yaml` can be read/written
- [ ] Session log can be appended to and read
- [ ] Profile cache can save/load YAML profiles
- [ ] Jupyter adapter can load/save/modify notebooks
- [ ] Kernel manager can execute code
- [ ] AST parser extracts definitions and references
- [ ] Agent skill (SKILL.md) is complete
- [ ] All unit tests pass

---

## Files Created

```
src/dasa/
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
├── session/
│   ├── __init__.py
│   ├── context.py
│   ├── log.py
│   └── profiles.py
└── output/
    ├── __init__.py
    └── formatter.py
skills/
└── notebook/
    └── SKILL.md
pyproject.toml
```

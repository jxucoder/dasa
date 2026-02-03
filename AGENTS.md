# AGENTS.md

Instructions for AI agents working on the DASA (Data Science Agent) project.

## Project Overview

DASA is an open source Data Science Agent toolkit that provides specialized capabilities for notebook-based data science work:

- **Understanding Tools**: `profile`, `validate`, `deps` - understand data and notebook state
- **Execution Tools**: `run`, `replay` - execute cells with rich error context
- **State Tools**: `vars`, `stale`, `kernel` - manage notebook state
- **Manipulation Tools**: `add`, `edit`, `delete`, `move` - modify notebooks

See `docs/PLAN.md` for the full implementation plan.

## Python Environment

**Always use `uv` for Python package management.**

### Common Commands

```bash
# Create virtual environment
uv venv

# Activate virtual environment
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate     # Windows

# Install dependencies
uv pip install -e ".[dev]"

# Add a new dependency
uv add <package>

# Add a dev dependency
uv add --dev <package>

# Run a command in the virtual environment
uv run <command>

# Sync dependencies from pyproject.toml
uv sync
```

### Project Setup

```bash
# Initial setup
uv venv
uv pip install -e ".[dev]"
```

## Code Style

- Use type hints for all function signatures
- Follow PEP 8 conventions
- Use `ruff` for linting and formatting
- Write docstrings for public functions and classes

## Project Structure

```
dasa/
├── src/dasa/           # Main package source
│   ├── cli/            # CLI commands (Typer)
│   ├── notebook/       # Format adapters (Jupyter, Marimo)
│   ├── analysis/       # Analysis engines (AST, profiling)
│   └── output/         # Output formatting
├── eval/               # Evaluation infrastructure
├── tests/              # Unit tests
├── docs/               # Documentation
└── skills/             # Agent skills
```

## Development Workflow

1. **Test-Driven Development**: Build evaluation infrastructure first, then implement features
2. **Measure Progress**: Every feature should show measurable improvement on eval tasks
3. **Small PRs**: Keep pull requests focused on single features or fixes

## Key Files

- `docs/PLAN.md` - Implementation plan and roadmap
- `docs/EVAL.md` - Evaluation framework details
- `docs/ARCHITECTURE.md` - Technical architecture
- `docs/CLI.md` - CLI reference

## Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=dasa

# Run specific test file
uv run pytest tests/test_cli/test_profile.py
```

## CLI Development

The CLI uses Typer. Each command is in its own module under `src/dasa/cli/`.

```bash
# Run the CLI during development
uv run dasa <command>

# Or after installing
dasa <command>
```

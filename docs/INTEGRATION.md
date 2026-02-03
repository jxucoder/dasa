# DASA Integration Guide

How to integrate DASA with different coding agents and environments.

## Overview

DASA provides two primary integration methods:

1. **Agent Skill** - A SKILL.md file that teaches agents best practices
2. **CLI Tools** - Commands any agent can run via bash

Both methods are designed to be universal and work with any coding agent.

---

## Method 1: Agent Skill

The Agent Skill teaches coding agents how to work with notebooks effectively.

### Installation

Copy the skill file to your project or global skills directory:

```bash
# For Cursor
mkdir -p .cursor/skills
cp $(pip show dasa | grep Location | cut -d' ' -f2)/dasa/skills/notebook/SKILL.md .cursor/skills/

# For Claude Code
mkdir -p .claude/skills
cp $(pip show dasa | grep Location | cut -d' ' -f2)/dasa/skills/notebook/SKILL.md .claude/skills/notebook/

# For Pi Agent
mkdir -p .pi/skills
cp $(pip show dasa | grep Location | cut -d' ' -f2)/dasa/skills/notebook/SKILL.md .pi/skills/

# For any agent supporting agentskills.io standard
mkdir -p skills
cp $(pip show dasa | grep Location | cut -d' ' -f2)/dasa/skills/notebook/SKILL.md skills/
```

### What the Skill Teaches

The skill instructs agents to:

1. **Validate state first** - Before working with a notebook, run `dasa validate`
2. **Profile data before coding** - Use `dasa profile --var df` before writing code that uses `df`
3. **Check dependencies** - Use `dasa deps` before modifying cells
4. **Handle long operations** - Use `dasa run --async` for training
5. **Verify reproducibility** - Use `dasa replay` before sharing

### Skill Triggers

The skill is automatically loaded when the agent encounters:
- Files with `.ipynb` extension
- Mentions of "notebook", "jupyter", "colab", "marimo"
- Data science tasks

---

## Method 2: CLI Tools

Any agent that can execute bash commands can use DASA tools.

### Basic Usage Pattern

```python
# Agent's internal reasoning:
# "I need to add a visualization. First, let me understand the data."

# Agent executes:
result = run_bash("dasa profile notebook.ipynb --var sales_data")

# Agent sees:
# DataFrame: sales_data (10000 rows × 5 columns)
# Columns:
#   region      object     4 unique: ['North', 'South', 'East', 'West']
#   revenue     float64    min=100, max=50000, mean=5200
#   ...

# Agent now knows the exact column names and types
```

### Common Workflows

#### Workflow 1: Add a Visualization

```bash
# 1. Understand the data
dasa profile notebook.ipynb --var df

# 2. Check where to add the cell
dasa cells notebook.ipynb

# 3. Add the visualization
dasa add notebook.ipynb --after 3 --code "
import matplotlib.pyplot as plt
plt.bar(df['region'], df['revenue'])
plt.title('Revenue by Region')
"

# 4. Run and verify
dasa run notebook.ipynb --cell 4
```

#### Workflow 2: Debug a Failing Cell

```bash
# 1. Run the cell to see the error
dasa run notebook.ipynb --cell 5

# Output shows:
# Error: KeyError: 'revenue_usd'
# Available columns: revenue, cost, user_id
# Suggestion: Did you mean 'revenue'?

# 2. Profile the DataFrame to understand structure
dasa profile notebook.ipynb --var df

# 3. Fix the code
dasa edit notebook.ipynb --cell 5 --code "df['profit'] = df['revenue'] - df['cost']"

# 4. Re-run
dasa run notebook.ipynb --cell 5
```

#### Workflow 3: Handle Long Training

```bash
# 1. Start training in background
dasa run notebook.ipynb --cell 4 --async
# Output: Started job abc123

# 2. Check progress periodically
dasa status abc123
# Output: Epoch 5/100, loss=0.234

# 3. Continue when done
dasa status abc123
# Output: COMPLETED (45 minutes)

# 4. Run evaluation
dasa run notebook.ipynb --cell 5
```

#### Workflow 4: Prepare for Sharing

```bash
# 1. Validate state
dasa validate notebook.ipynb

# 2. If issues found, replay from scratch
dasa replay notebook.ipynb

# 3. Check reproducibility report
# Output shows:
# Reproducibility: 100%
# All cells pass
```

---

## Integration with Specific Agents

### Cursor

Cursor supports both Agent Skills and MCP servers.

**Option 1: Agent Skill (Recommended)**

```bash
mkdir -p .cursor/skills
cp SKILL.md .cursor/skills/notebook.md
```

**Option 2: MCP Server (Optional)**

```json
// ~/.cursor/mcp.json
{
  "mcpServers": {
    "dasa": {
      "command": "dasa",
      "args": ["mcp-serve"]
    }
  }
}
```

### Claude Code

Claude Code supports plugins with skills, commands, and hooks.

**Full Plugin Structure:**

```
dasa-claude-plugin/
├── .claude-plugin/
│   └── plugin.json
├── skills/
│   └── notebook/
│       └── SKILL.md
├── commands/
│   ├── profile.md        # /profile command
│   ├── validate.md       # /validate command
│   └── run-cell.md       # /run-cell command
└── README.md
```

**plugin.json:**
```json
{
  "name": "dasa",
  "version": "1.0.0",
  "description": "Data Science Agent tools for notebooks"
}
```

### OpenCode

OpenCode supports MCP servers via config.

```jsonc
// opencode.jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "dasa": {
      "type": "local",
      "command": ["dasa", "mcp-serve"],
      "enabled": true
    }
  }
}
```

### Codex CLI

Codex supports external tools via bash. No special configuration needed.

```bash
# Agent can simply run
dasa profile notebook.ipynb --var df
```

### GitHub Copilot

Copilot doesn't execute commands directly, but can suggest DASA commands in its responses when the skill is present.

---

## Environment Setup

### Virtual Environments

DASA respects the active Python environment:

```bash
# Activate your project's environment
source venv/bin/activate

# DASA will use this environment's packages
dasa profile notebook.ipynb --var df
```

### Conda Environments

```bash
conda activate myproject
dasa run notebook.ipynb --cell 3
```

### Docker

```dockerfile
FROM python:3.11

# Install DASA
RUN pip install dasa

# Your application
COPY . /app
WORKDIR /app

# DASA is available
RUN dasa validate notebook.ipynb
```

---

## Output Format

All DASA output is designed to be:

1. **Parseable** - Structured, consistent format
2. **Actionable** - Includes suggestions for fixing issues
3. **LLM-friendly** - Clear, scannable by language models

### JSON Output

For programmatic use, add `--format json`:

```bash
dasa profile notebook.ipynb --var df --format json
```

```json
{
  "name": "df",
  "type": "DataFrame",
  "shape": [50000, 12],
  "memory_bytes": 4800000,
  "columns": [
    {
      "name": "user_id",
      "dtype": "int64",
      "unique_count": 50000,
      "null_count": 0
    },
    ...
  ],
  "issues": [
    "revenue: 4.7% null values",
    "revenue: has negative values"
  ]
}
```

---

## Troubleshooting

### Kernel Not Starting

```bash
# Check if Jupyter is installed
pip install jupyter

# Try starting manually
dasa kernel notebook.ipynb start
```

### Permission Issues

```bash
# Make sure DASA can write to notebook directory
chmod 755 notebook_directory/
```

### Timeout on Long Operations

```bash
# Use async for long operations
dasa run notebook.ipynb --cell 4 --async

# Or increase timeout
dasa run notebook.ipynb --cell 4 --timeout 3600
```

### Output Not Captured

```bash
# Make sure kernel is running
dasa kernel notebook.ipynb status

# Restart if needed
dasa kernel notebook.ipynb restart
```

---

## Best Practices

### For Agent Developers

1. **Always validate first** - Run `dasa validate` before making changes
2. **Profile before coding** - Use `dasa profile` to understand data
3. **Check dependencies** - Use `dasa deps` before modifying cells
4. **Handle async** - Use `--async` for anything > 30 seconds
5. **Verify before sharing** - Use `dasa replay` to check reproducibility

### For CI/CD

```yaml
# .github/workflows/notebook.yml
- name: Validate notebooks
  run: |
    pip install dasa
    dasa validate notebooks/*.ipynb --strict
    
- name: Check reproducibility
  run: |
    dasa replay notebooks/*.ipynb --strict
```

### For Teams

1. Add SKILL.md to project repository
2. Document expected data formats
3. Set up pre-commit hooks with `dasa validate`
4. Use `dasa replay` in CI to catch reproducibility issues

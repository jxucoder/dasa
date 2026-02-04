# DASA - Working with Jupyter Notebooks

DASA is a CLI toolkit for working with Jupyter notebooks. Use these commands when you need to understand, validate, or execute notebook code.

## When to Use DASA

Use DASA when:
- User asks about a notebook's structure or contents
- You need to run specific cells in a notebook
- You need to check for issues in notebook code
- You need to understand cell dependencies
- You need to modify notebook cells

## Commands

### Understanding Notebooks

```bash
# Get notebook overview (cell count, imports, structure)
dasa profile notebook.ipynb

# Check for issues (undefined variables, unused imports, out-of-order execution)
dasa validate notebook.ipynb

# Show cell dependencies (which cells depend on which)
dasa deps notebook.ipynb

# List all cells with previews
dasa cells notebook.ipynb

# Show notebook metadata and info
dasa info notebook.ipynb
```

### Executing Code

```bash
# Run a specific cell
dasa run notebook.ipynb --cell 5

# Run a range of cells
dasa run notebook.ipynb --from 2 --to 5

# Run all cells
dasa run notebook.ipynb --all

# Run stale cells (cells that need re-execution)
dasa run notebook.ipynb --stale

# Run in background for long-running cells
dasa run notebook.ipynb --cell 5 --async

# Check background job status
dasa status

# Get results from completed job
dasa result <job-id>
```

### Modifying Notebooks

```bash
# Add a new code cell
dasa add notebook.ipynb "print('hello')"

# Add at specific position
dasa add notebook.ipynb "x = 1" --after 2

# Add markdown cell
dasa add notebook.ipynb --markdown "# Section Title"

# Edit existing cell
dasa edit notebook.ipynb --cell 3 "new_code = 'here'"

# Delete a cell
dasa delete notebook.ipynb --cell 5

# Move a cell
dasa move notebook.ipynb --cell 3 --to 7
```

### State Inspection

```bash
# List variables defined in notebook
dasa vars notebook.ipynb

# Show which cells are stale (need re-running)
dasa stale notebook.ipynb

# Show cell outputs
dasa outputs notebook.ipynb
dasa outputs notebook.ipynb --cell 3
```

### Kernel Management

```bash
# Check kernel status
dasa kernel status notebook.ipynb

# Restart kernel
dasa kernel restart notebook.ipynb

# Interrupt running execution
dasa kernel interrupt notebook.ipynb
```

## Workflow Patterns

### First time looking at a notebook
```bash
dasa profile notebook.ipynb   # Understand structure
dasa validate notebook.ipynb  # Check for issues
```

### Before modifying code
```bash
dasa deps notebook.ipynb --cell 5  # See what depends on cell 5
```

### After modifying a cell
```bash
dasa stale notebook.ipynb     # See what needs re-running
dasa run notebook.ipynb --stale  # Re-run affected cells
```

### Long-running computation
```bash
dasa run notebook.ipynb --cell 10 --async  # Start in background
dasa status                                 # Check progress
dasa result <job-id>                        # Get results when done
```

## Output Formats

Most commands support `--format json` for structured output:
```bash
dasa profile notebook.ipynb --format json
dasa cells notebook.ipynb --format json
```

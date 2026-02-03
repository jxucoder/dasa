# Sprint 5: Manipulation Tools

**Goal:** Implement notebook manipulation tools: `add`, `edit`, `delete`, `move`.

**Duration:** ~2 days

**Prerequisite:** Sprint 4 (State tools)

---

## Deliverables

| # | Deliverable | Description |
|---|-------------|-------------|
| 1 | `dasa add` | Add new cells to notebook |
| 2 | `dasa edit` | Edit existing cell content |
| 3 | `dasa delete` | Delete cells with warnings |
| 4 | `dasa move` | Reorder cells |

---

## Tasks

### 5.1 Add Command

```bash
# Add code cell after cell 3
dasa add notebook.ipynb --after 3 --code "plt.bar(df['region'], df['sales'])"

# Add markdown cell at the beginning
dasa add notebook.ipynb --at 0 --markdown "# Sales Analysis Report"
```

**Features:**
- Add code or markdown cells
- Position: `--at N`, `--after N`, `--before N`
- Validate syntax before adding
- Show dependency impact

---

### 5.2 Edit Command

```bash
dasa edit notebook.ipynb --cell 3 --code "plt.bar(df['region'], df['revenue'])"

# Output:
# Cell 3 updated.
# Previous: plt.bar(df['region'], df['sales'])
# New: plt.bar(df['region'], df['revenue'])
# 
# ⚠ This cell has downstream dependents: Cell 4, Cell 5
```

**Features:**
- Replace cell content
- Show diff
- Warn about downstream dependencies

---

### 5.3 Delete Command

```bash
dasa delete notebook.ipynb --cell 5

# Output:
# ⚠ Cell 5 defines variables used elsewhere:
#   - model (used in Cell 6)
# 
# Delete anyway? [y/N]
```

**Features:**
- Warn about dependent cells
- Require `--force` to skip confirmation
- Update indices after deletion

---

### 5.4 Move Command

```bash
dasa move notebook.ipynb --cell 5 --to 2

# Output:
# Moved Cell 5 to position 2
# New order: [0, 1, 5, 2, 3, 4, 6, ...]
```

**Features:**
- Reorder cells
- Validate dependencies don't break
- Warn if move creates invalid state

---

## Acceptance Criteria

- [ ] `dasa add` creates new cells at correct position
- [ ] `dasa edit` updates cell content with diff
- [ ] `dasa delete` warns about dependencies
- [ ] `dasa move` reorders cells safely
- [ ] All commands save notebook after modification

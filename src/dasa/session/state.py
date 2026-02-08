"""Staleness tracking via .dasa/state.json."""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Optional


class StateTracker:
    """Track cell code hashes for staleness detection."""

    def __init__(self, project_dir: str = "."):
        self.state_path = Path(project_dir) / ".dasa" / "state.json"

    def _load(self) -> dict:
        """Load state from disk."""
        if not self.state_path.exists():
            return {}
        with open(self.state_path) as f:
            return json.load(f)

    def _save(self, state: dict) -> None:
        """Save state to disk."""
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_path, "w") as f:
            json.dump(state, f, indent=2)

    def update_cell(self, notebook: str, cell_index: int, source: str) -> None:
        """Update the code hash for a cell after execution."""
        state = self._load()
        if notebook not in state:
            state[notebook] = {"cells": {}}

        code_hash = hashlib.sha256(source.encode()).hexdigest()[:12]
        state[notebook]["cells"][str(cell_index)] = {
            "code_hash": code_hash,
            "last_run": datetime.now().isoformat(),
        }
        self._save(state)

    def is_stale(self, notebook: str, cell_index: int, current_source: str) -> bool:
        """Check if a cell's code has changed since last execution."""
        state = self._load()
        nb_state = state.get(notebook, {}).get("cells", {})
        cell_state = nb_state.get(str(cell_index))

        if cell_state is None:
            return True  # Never executed via dasa

        current_hash = hashlib.sha256(current_source.encode()).hexdigest()[:12]
        return cell_state["code_hash"] != current_hash

    def get_stale_cells(self, notebook: str, cells: list[tuple[int, str]]) -> list[int]:
        """Get indices of cells whose code has changed since last execution."""
        return [idx for idx, source in cells if self.is_stale(notebook, idx, source)]

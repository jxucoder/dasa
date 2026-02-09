"""Staleness tracking via .dasa/state.json."""

import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional


class StateTracker:
    """Track cell code hashes for staleness detection."""

    def __init__(self, project_dir: str = ".", session_dir: str | None = None):
        if session_dir:
            self.state_path = Path(session_dir) / "state.json"
        else:
            self.state_path = Path(project_dir) / ".dasa" / "state.json"

    @staticmethod
    def _normalize_path(path: str) -> str:
        """Normalize notebook path for consistent state tracking.

        Resolves relative paths so './nb.ipynb' and 'nb.ipynb' map to the same key.
        """
        return str(Path(path).resolve())

    def _load(self) -> dict:
        """Load state from disk. Returns empty dict on missing or corrupted files."""
        if not self.state_path.exists():
            return {}
        try:
            with open(self.state_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(
                f"Warning: corrupted {self.state_path}, resetting: {e}",
                file=sys.stderr,
            )
            return {}

    def _save(self, state: dict) -> None:
        """Save state to disk atomically (temp file + rename)."""
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

        fd, tmp_path = tempfile.mkstemp(
            dir=self.state_path.parent,
            suffix=".tmp",
        )
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(state, f, indent=2)
            os.replace(tmp_path, self.state_path)
        except BaseException:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def update_cell(self, notebook: str, cell_index: int, source: str) -> None:
        """Update the code hash for a cell after execution."""
        state = self._load()
        key = self._normalize_path(notebook)
        if key not in state:
            state[key] = {"cells": {}}

        code_hash = hashlib.sha256(source.encode()).hexdigest()[:12]
        state[key]["cells"][str(cell_index)] = {
            "code_hash": code_hash,
            "last_run": datetime.now().isoformat(),
        }
        self._save(state)

    def is_stale(self, notebook: str, cell_index: int, current_source: str) -> bool:
        """Check if a cell's code has changed since last execution.

        Returns True if the cell was never executed via dasa or if its code changed.
        """
        state = self._load()
        key = self._normalize_path(notebook)
        nb_state = state.get(key, {}).get("cells", {})
        cell_state = nb_state.get(str(cell_index))

        if cell_state is None:
            return True  # Never executed via dasa

        current_hash = hashlib.sha256(current_source.encode()).hexdigest()[:12]
        return cell_state["code_hash"] != current_hash

    def was_executed(self, notebook: str, cell_index: int) -> bool:
        """Check if a cell was ever executed via dasa run (regardless of staleness)."""
        state = self._load()
        key = self._normalize_path(notebook)
        nb_state = state.get(key, {}).get("cells", {})
        return str(cell_index) in nb_state

    def was_executed_current(
        self, notebook: str, cell_index: int, current_source: str
    ) -> bool:
        """Check if a cell was executed via dasa and its code hasn't changed since."""
        return self.was_executed(notebook, cell_index) and not self.is_stale(
            notebook, cell_index, current_source
        )

    def get_stale_cells(
        self, notebook: str, cells: list[tuple[int, str]]
    ) -> list[int]:
        """Get indices of cells whose code has changed since last execution."""
        return [idx for idx, source in cells if self.is_stale(notebook, idx, source)]

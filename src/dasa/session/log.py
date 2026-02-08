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

"""Cached data profiles (.dasa/profiles/)."""

import os
import sys
import tempfile
from pathlib import Path
from typing import Optional
import yaml


class ProfileCache:
    """Cache and retrieve data profiles."""

    def __init__(self, project_dir: str = ".", session_dir: str | None = None):
        if session_dir:
            self.profiles_dir = Path(session_dir) / "profiles"
        else:
            self.profiles_dir = Path(project_dir) / ".dasa" / "profiles"

    def save(self, var_name: str, profile: dict) -> Path:
        """Save a profile to cache atomically."""
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        path = self.profiles_dir / f"{var_name}.yaml"

        fd, tmp_path = tempfile.mkstemp(
            dir=self.profiles_dir,
            suffix=".tmp",
        )
        try:
            with os.fdopen(fd, "w") as f:
                yaml.dump(profile, f, default_flow_style=False, sort_keys=False)
            os.replace(tmp_path, path)
        except BaseException:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

        return path

    def load(self, var_name: str) -> Optional[dict]:
        """Load a cached profile. Returns None on missing or corrupted files."""
        path = self.profiles_dir / f"{var_name}.yaml"
        if not path.exists():
            return None

        try:
            with open(path) as f:
                return yaml.safe_load(f)
        except (yaml.YAMLError, OSError) as e:
            print(
                f"Warning: corrupted profile {path}, skipping: {e}",
                file=sys.stderr,
            )
            return None

    def list_profiles(self) -> list[str]:
        """List all cached profile names."""
        if not self.profiles_dir.exists():
            return []
        return [p.stem for p in self.profiles_dir.glob("*.yaml")]

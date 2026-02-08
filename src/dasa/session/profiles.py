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

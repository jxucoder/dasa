"""DASA: Data Science Agent toolkit."""

__version__ = "0.1.0"

from pathlib import Path

# Path to the agent skill file
SKILL_PATH = Path(__file__).parent.parent.parent / "skills" / "notebook" / "SKILL.md"

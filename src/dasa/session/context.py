"""Project context management (.dasa/context.yaml)."""

from pathlib import Path
from typing import Optional
import yaml
from dataclasses import dataclass, field


@dataclass
class ProjectContext:
    """Project-level context persisted in .dasa/context.yaml."""
    name: Optional[str] = None
    goal: Optional[str] = None
    status: Optional[str] = None
    notebook: Optional[str] = None
    constraints: list[str] = field(default_factory=list)
    approaches: list[dict] = field(default_factory=list)
    data: dict = field(default_factory=dict)


class ContextManager:
    """Read/write .dasa/context.yaml."""

    def __init__(self, project_dir: str = "."):
        self.project_dir = Path(project_dir)
        self.dasa_dir = self.project_dir / ".dasa"
        self.context_path = self.dasa_dir / "context.yaml"

    def ensure_session(self) -> None:
        """Create .dasa/ directory structure if it doesn't exist."""
        self.dasa_dir.mkdir(exist_ok=True)
        (self.dasa_dir / "profiles").mkdir(exist_ok=True)
        if not (self.dasa_dir / "log").exists():
            (self.dasa_dir / "log").touch()

    def read(self) -> ProjectContext:
        """Read project context."""
        if not self.context_path.exists():
            return ProjectContext()

        with open(self.context_path) as f:
            data = yaml.safe_load(f) or {}

        project = data.get("project", {})
        return ProjectContext(
            name=project.get("name"),
            goal=project.get("goal"),
            status=project.get("status"),
            notebook=project.get("notebook"),
            constraints=project.get("constraints", []),
            approaches=data.get("approaches", []),
            data=data.get("data", {}),
        )

    def write(self, context: ProjectContext) -> None:
        """Write project context."""
        self.ensure_session()

        data = {
            "project": {
                "name": context.name,
                "goal": context.goal,
                "status": context.status,
                "notebook": context.notebook,
                "constraints": context.constraints,
            },
            "approaches": context.approaches,
            "data": context.data,
        }

        # Remove None values from project
        data["project"] = {k: v for k, v in data["project"].items() if v is not None}

        with open(self.context_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    def update(self, **kwargs) -> ProjectContext:
        """Update specific fields in context."""
        context = self.read()
        for key, value in kwargs.items():
            if hasattr(context, key) and value is not None:
                setattr(context, key, value)
        self.write(context)
        return context

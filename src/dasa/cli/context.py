"""Context command — project memory management."""

import json
from typing import Optional

import typer
from rich.console import Console

from dasa.session.context import ContextManager
from dasa.session.log import SessionLog
from dasa.session.profiles import ProfileCache

console = Console()


def context(
    set_goal: Optional[str] = typer.Option(None, "--set-goal", help="Set project goal"),
    set_status: Optional[str] = typer.Option(None, "--set-status", help="Set project status"),
    set_name: Optional[str] = typer.Option(None, "--set-name", help="Set project name"),
    log_message: Optional[str] = typer.Option(None, "--log", help="Append to decision log"),
    log_only: bool = typer.Option(False, "--log-only", help="Show only recent log"),
    last: int = typer.Option(20, "--last", help="Number of recent log entries"),
    format: str = typer.Option("text", "--format", "-f", help="Output format: text, json"),
) -> None:
    """Read or update project context and memory."""
    ctx_mgr = ContextManager()
    session_log = SessionLog()
    profile_cache = ProfileCache()

    # Handle writes
    if any([set_goal, set_status, set_name]):
        ctx_mgr.ensure_session()
        ctx_mgr.update(goal=set_goal, status=set_status, name=set_name)

        if set_goal:
            session_log.append("user", f"Goal: {set_goal}")
            console.print(f"[green]Goal set:[/green] {set_goal}")
        if set_status:
            session_log.append("user", f"Status: {set_status}")
            console.print(f"[green]Status set:[/green] {set_status}")
        if set_name:
            console.print(f"[green]Name set:[/green] {set_name}")
        return

    if log_message:
        ctx_mgr.ensure_session()
        session_log.append("agent", log_message)
        console.print(f"[green]Logged:[/green] {log_message}")
        return

    # Handle reads
    ctx = ctx_mgr.read()

    if log_only:
        entries = session_log.read(last_n=last)
        if not entries:
            console.print("[dim]No log entries yet.[/dim]")
        for entry in entries:
            console.print(f"  {entry}")
        return

    if format == "json":
        _output_json(ctx, session_log, profile_cache)
        return

    # Full context display
    _print_context(ctx, session_log, profile_cache)


def _print_context(ctx, session_log, profile_cache) -> None:
    """Print full project context."""
    if not ctx.name and not ctx.goal:
        console.print("[dim]No project context yet. Set one with:[/dim]")
        console.print("  dasa context --set-goal 'Your goal here'")
        return

    # Project info
    if ctx.name:
        console.print(f"\n[bold]Project:[/bold] {ctx.name}")
    if ctx.goal:
        console.print(f"[bold]Goal:[/bold] {ctx.goal}")
    if ctx.status:
        console.print(f"[bold]Status:[/bold] {ctx.status}")
    if ctx.notebook:
        console.print(f"[bold]Notebook:[/bold] {ctx.notebook}")

    # Constraints
    if ctx.constraints:
        console.print(f"\n[bold]Constraints:[/bold]")
        for c in ctx.constraints:
            console.print(f"  - {c}")

    # Data profiles
    profiles = profile_cache.list_profiles()
    if profiles:
        console.print(f"\n[bold]Data:[/bold]")
        for name in profiles:
            profile = profile_cache.load(name)
            if profile:
                shape = profile.get("shape", [])
                shape_str = f"{shape[0]:,} rows x {shape[1]} cols" if len(shape) == 2 else ""
                console.print(f"  {name}: {shape_str}")

    # Approaches
    if ctx.approaches:
        console.print(f"\n[bold]Tried:[/bold]")
        for approach in ctx.approaches:
            status_icon = "OK" if approach.get("status") == "current" else "X"
            name = approach.get("name", "unknown")
            result = approach.get("result", "")
            reason = approach.get("reason", "")
            console.print(f"  {status_icon} {name} -- {result}")
            if reason:
                console.print(f"    {reason}")

    # Recent log
    entries = session_log.read(last_n=10)
    if entries:
        console.print(f"\n[bold]Recent:[/bold]")
        for entry in entries:
            console.print(f"  {entry}")

    console.print()


def _output_json(ctx, session_log, profile_cache) -> None:
    """Output context as JSON."""
    profiles = {}
    for name in profile_cache.list_profiles():
        profiles[name] = profile_cache.load(name)

    data = {
        "project": {
            "name": ctx.name,
            "goal": ctx.goal,
            "status": ctx.status,
            "notebook": ctx.notebook,
            "constraints": ctx.constraints,
        },
        "approaches": ctx.approaches,
        "data": ctx.data,
        "profiles": profiles,
        "recent_log": session_log.read(last_n=20),
    }
    console.print(json.dumps(data, indent=2, default=str))

"""MCP serve command — start DASA as an MCP server."""

import typer
from rich.console import Console

console = Console()


def mcp_serve() -> None:
    """Start DASA as an MCP server (Model Context Protocol)."""
    try:
        from dasa.mcp.server import run_mcp_server
        run_mcp_server()
    except ImportError:
        console.print("[red]Error: MCP package not installed.[/red]")
        console.print("Install with: pip install mcp")
        raise typer.Exit(1)

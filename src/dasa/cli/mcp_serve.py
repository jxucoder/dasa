"""MCP serve command implementation."""

import asyncio
import json
import sys
from typing import Optional

import typer
from rich.console import Console

console = Console()


def mcp_serve(
    transport: str = typer.Option("stdio", "--transport", "-t", help="Transport type: stdio"),
) -> None:
    """Start DASA as an MCP server."""

    from dasa.mcp.server import create_server

    server = create_server()

    console.print(f"[bold]DASA MCP Server[/bold]", err=True)
    console.print(f"Version: {server.version}", err=True)
    console.print(f"Transport: {transport}", err=True)
    console.print(f"Tools: {len(server.get_tools())}", err=True)
    console.print("", err=True)

    if transport == "stdio":
        asyncio.run(_run_stdio_server(server))
    else:
        console.print(f"[red]Unknown transport: {transport}[/red]", err=True)
        raise typer.Exit(1)


async def _run_stdio_server(server) -> None:
    """Run server over stdio transport."""
    console.print("[dim]Listening on stdin...[/dim]", err=True)

    while True:
        try:
            # Read line from stdin
            line = await asyncio.get_event_loop().run_in_executor(
                None, sys.stdin.readline
            )

            if not line:
                break

            line = line.strip()
            if not line:
                continue

            # Parse JSON-RPC request
            try:
                request = json.loads(line)
            except json.JSONDecodeError:
                _send_error(-32700, "Parse error")
                continue

            # Handle request
            method = request.get("method", "")
            params = request.get("params", {})
            request_id = request.get("id")

            if method == "initialize":
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {}
                        },
                        "serverInfo": {
                            "name": server.name,
                            "version": server.version
                        }
                    }
                }

            elif method == "tools/list":
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "tools": server.get_tools()
                    }
                }

            elif method == "tools/call":
                tool_name = params.get("name", "")
                tool_args = params.get("arguments", {})

                result = await server.call_tool(tool_name, tool_args)

                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(result, indent=2)
                            }
                        ]
                    }
                }

            elif method == "notifications/initialized":
                # No response needed for notifications
                continue

            else:
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                }

            # Send response
            print(json.dumps(response), flush=True)

        except KeyboardInterrupt:
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]", err=True)


def _send_error(code: int, message: str, request_id: Optional[int] = None) -> None:
    """Send JSON-RPC error response."""
    response = {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": code,
            "message": message
        }
    }
    print(json.dumps(response), flush=True)

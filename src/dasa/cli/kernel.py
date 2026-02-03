"""Kernel command implementation."""

import json
from typing import Optional

import typer
from rich.console import Console

from dasa.notebook.jupyter import JupyterAdapter
from dasa.notebook.kernel import KernelManager

console = Console()

# Create subcommand app
kernel_app = typer.Typer(help="Kernel management commands")


@kernel_app.command("status")
def kernel_status(
    notebook: str = typer.Argument(..., help="Path to notebook"),
    format_output: str = typer.Option("text", "--format", "-f", help="Output format"),
) -> None:
    """Show kernel status."""

    adapter = JupyterAdapter(notebook)
    kernel = KernelManager(adapter.kernel_spec or "python3")

    try:
        kernel.start()

        # Get kernel info
        info_code = '''
import json
import sys
import os

info = {
    "python_version": sys.version.split()[0],
    "executable": sys.executable,
    "pid": os.getpid(),
    "cwd": os.getcwd()
}

# Try to get memory usage
try:
    import psutil
    process = psutil.Process(os.getpid())
    info["memory_mb"] = round(process.memory_info().rss / 1024 / 1024, 1)
except:
    pass

# Count defined variables
user_vars = [k for k in globals().keys() if not k.startswith('_') and k not in ['In', 'Out', 'get_ipython', 'exit', 'quit']]
info["variables"] = len(user_vars)

print(json.dumps(info))
'''
        result = kernel.execute(info_code)

        if result.success:
            info = json.loads(result.stdout.strip())

            if format_output == "json":
                console.print(json.dumps(info, indent=2))
            else:
                console.print("\n[bold]Kernel Status[/bold]\n")
                console.print(f"  Status: [green]Running[/green]")
                console.print(f"  Python: {info.get('python_version', 'unknown')}")
                console.print(f"  PID: {info.get('pid', 'unknown')}")
                if info.get('memory_mb'):
                    console.print(f"  Memory: {info['memory_mb']} MB")
                console.print(f"  Variables: {info.get('variables', 0)}")
        else:
            console.print("[red]Failed to get kernel info[/red]")

    finally:
        kernel.shutdown()


@kernel_app.command("restart")
def kernel_restart(
    notebook: str = typer.Argument(..., help="Path to notebook"),
) -> None:
    """Restart kernel (clears all state)."""

    adapter = JupyterAdapter(notebook)
    kernel = KernelManager(adapter.kernel_spec or "python3")

    try:
        kernel.start()
        console.print("Restarting kernel...", end=" ")
        kernel.restart()
        console.print("[green]Done[/green]")
        console.print("[dim]All variables and state cleared[/dim]")
    finally:
        kernel.shutdown()


@kernel_app.command("interrupt")
def kernel_interrupt(
    notebook: str = typer.Argument(..., help="Path to notebook"),
) -> None:
    """Interrupt running execution."""

    adapter = JupyterAdapter(notebook)
    kernel = KernelManager(adapter.kernel_spec or "python3")

    try:
        kernel.start()
        kernel.interrupt()
        console.print("[yellow]Kernel interrupted[/yellow]")
    finally:
        kernel.shutdown()

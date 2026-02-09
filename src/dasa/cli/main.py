"""DASA CLI entry point."""

import typer
from rich.console import Console

app = typer.Typer(
    name="dasa",
    help="Data Science Agent toolkit for notebooks",
    no_args_is_help=True,
    invoke_without_command=True,
)

console = Console()


@app.callback()
def main(
    show_version: bool = typer.Option(
        False, "--version", "-V", help="Show version and exit"
    ),
) -> None:
    """DASA: Data Science Agent toolkit for notebooks."""
    if show_version:
        from dasa import __version__

        console.print(f"dasa {__version__}")
        raise typer.Exit()


@app.command()
def version():
    """Show DASA version."""
    from dasa import __version__

    console.print(f"dasa {__version__}")


# Sprint 2: Eyes
from dasa.cli.profile import profile
from dasa.cli.check import check

app.command()(profile)
app.command()(check)

# Sprint 3: Hands + Memory
from dasa.cli.run import run
from dasa.cli.context import context

app.command()(run)
app.command()(context)

# Sprint 4: Multi-Agent
from dasa.cli.status import status

app.command()(status)

# Sprint 5: Extensions
from dasa.cli.replay import replay
from dasa.cli.mcp_serve import mcp_serve

app.command()(replay)
app.command(name="mcp-serve")(mcp_serve)


if __name__ == "__main__":
    app()

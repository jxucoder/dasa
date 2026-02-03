"""DASA CLI entry point."""

import typer
from rich.console import Console

from dasa.cli.profile import profile
from dasa.cli.validate import validate
from dasa.cli.deps import deps
from dasa.cli.run import run
from dasa.cli.replay import replay

app = typer.Typer(
    name="dasa",
    help="Data Science Agent toolkit for notebooks",
    no_args_is_help=True
)

console = Console()

# Understanding tools
app.command()(profile)
app.command()(validate)
app.command()(deps)

# Execution tools
app.command()(run)
app.command()(replay)


@app.command()
def version() -> None:
    """Show DASA version."""
    from dasa import __version__
    console.print(f"dasa {__version__}")


if __name__ == "__main__":
    app()

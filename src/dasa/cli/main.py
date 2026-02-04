"""DASA CLI entry point."""

import typer
from rich.console import Console

# Sprint 2: Understanding tools
from dasa.cli.profile import profile
from dasa.cli.validate import validate
from dasa.cli.deps import deps

# Sprint 3: Execution tools
from dasa.cli.run import run
from dasa.cli.replay import replay

# Sprint 4: State tools
from dasa.cli.vars import vars_cmd
from dasa.cli.stale import stale
from dasa.cli.kernel import kernel_app

# Sprint 5: Manipulation tools
from dasa.cli.add import add
from dasa.cli.edit import edit
from dasa.cli.delete import delete
from dasa.cli.move import move

# Sprint 6: Info tools
from dasa.cli.info import info
from dasa.cli.cells import cells
from dasa.cli.outputs import outputs
from dasa.cli.status import status
from dasa.cli.cancel import cancel
from dasa.cli.result import result

# Sprint 7: Extensions
from dasa.cli.mcp_serve import mcp_serve

app = typer.Typer(
    name="dasa",
    help="Data Science Agent toolkit for notebooks",
    no_args_is_help=True
)

console = Console()

# Understanding tools (Sprint 2)
app.command()(profile)
app.command()(validate)
app.command()(deps)

# Execution tools (Sprint 3)
app.command()(run)
app.command()(replay)

# State tools (Sprint 4)
app.command("vars")(vars_cmd)
app.command()(stale)
app.add_typer(kernel_app, name="kernel")

# Manipulation tools (Sprint 5)
app.command()(add)
app.command()(edit)
app.command()(delete)
app.command()(move)

# Info tools (Sprint 6)
app.command()(info)
app.command()(cells)
app.command()(outputs)
app.command()(status)
app.command()(cancel)
app.command()(result)

# Extensions (Sprint 7)
app.command("mcp-serve")(mcp_serve)


@app.command()
def version() -> None:
    """Show DASA version."""
    from dasa import __version__
    console.print(f"dasa {__version__}")


if __name__ == "__main__":
    app()

"""Validate command implementation."""

import json

import typer
from rich.console import Console

from dasa.notebook.jupyter import JupyterAdapter
from dasa.analysis.state import StateAnalyzer

console = Console()


def validate(
    notebook: str = typer.Argument(..., help="Path to notebook"),
    strict: bool = typer.Option(False, "--strict", help="Fail on any warning"),
    format_output: str = typer.Option("text", "--format", "-f", help="Output format: text, json"),
) -> None:
    """Check notebook state for consistency issues."""

    adapter = JupyterAdapter(notebook)
    analyzer = StateAnalyzer()
    analysis = analyzer.analyze(adapter)

    if format_output == "json":
        console.print(json.dumps({
            "is_consistent": analysis.is_consistent,
            "issues": [
                {
                    "severity": i.severity,
                    "cell_index": i.cell_index,
                    "message": i.message,
                    "suggestion": i.suggestion
                }
                for i in analysis.issues
            ],
            "execution_order": analysis.execution_order,
            "correct_order": analysis.correct_order
        }, indent=2))
        return

    # Text output
    console.print("\n[bold]Notebook State Analysis[/bold]\n")

    if analysis.is_consistent and not analysis.issues:
        console.print("[green]OK Notebook state is consistent[/green]")
    elif analysis.is_consistent:
        console.print("[yellow]! Notebook state has warnings[/yellow]")
    else:
        console.print("[red]X INCONSISTENT STATE DETECTED[/red]")

    # Show issues
    if analysis.issues:
        console.print("\n[bold]Issues:[/bold]")
        for issue in analysis.issues:
            icon = "X" if issue.severity == "error" else "!"
            color = "red" if issue.severity == "error" else "yellow"
            console.print(f"  [{color}]{icon}[/{color}] Cell {issue.cell_index}: {issue.message}")
            if issue.suggestion:
                console.print(f"      -> {issue.suggestion}")

    # Show execution order
    if analysis.execution_order:
        console.print(f"\n[bold]Execution Order:[/bold]")
        order_str = " -> ".join(f"[{i}]" for i in analysis.execution_order)
        console.print(f"  Actual: {order_str}")

        correct_str = " -> ".join(f"[{i}]" for i in analysis.correct_order)
        if analysis.execution_order != analysis.correct_order:
            console.print(f"  Correct: {correct_str}")

    # Exit code
    if strict and analysis.issues:
        raise typer.Exit(1)
    elif not analysis.is_consistent:
        raise typer.Exit(1)

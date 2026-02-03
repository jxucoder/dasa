"""Outputs command implementation."""

import json
from typing import Any, Optional

import typer
from rich.console import Console

from dasa.notebook.jupyter import JupyterAdapter
from dasa.output.formatter import format_bytes

console = Console()


def outputs(
    notebook: str = typer.Argument(..., help="Path to notebook"),
    cell: int = typer.Option(..., "--cell", "-c", help="Cell index"),
    format_output: str = typer.Option("text", "--format", "-f", help="Output format: text, json"),
) -> None:
    """View cell outputs with descriptions."""

    adapter = JupyterAdapter(notebook)

    # Validate cell index
    if cell < 0 or cell >= len(adapter.cells):
        console.print(f"[red]Cell {cell} not found[/red]")
        raise typer.Exit(1)

    target_cell = adapter.get_cell(cell)

    if target_cell.cell_type != "code":
        console.print(f"[yellow]Cell {cell} is a {target_cell.cell_type} cell (no outputs)[/yellow]")
        return

    if not target_cell.outputs:
        console.print(f"[dim]Cell {cell} has no outputs[/dim]")
        return

    outputs_data = []

    for i, output in enumerate(target_cell.outputs):
        output_info = analyze_output(output)
        output_info["index"] = i
        outputs_data.append(output_info)

    if format_output == "json":
        console.print(json.dumps(outputs_data, indent=2))
        return

    # Text output
    console.print(f"\n[bold]Cell {cell} Outputs ({len(outputs_data)} total)[/bold]\n")

    for out in outputs_data:
        console.print(f"[bold]Output {out['index']}:[/bold]")
        console.print(f"  Type: {out['type']}")

        if out.get("size"):
            console.print(f"  Size: {format_bytes(out['size'])}")

        if out.get("description"):
            console.print(f"\n  [bold]Description:[/bold]")
            for line in out["description"]:
                console.print(f"    {line}")

        if out.get("preview"):
            console.print(f"\n  [bold]Preview:[/bold]")
            for line in out["preview"][:5]:
                console.print(f"    {line}")

        console.print()


def analyze_output(output: dict[str, Any]) -> dict[str, Any]:
    """Analyze an output and generate description."""

    output_type = output.get("output_type", "unknown")
    result: dict[str, Any] = {"type": output_type}

    if output_type == "stream":
        text = output.get("text", "")
        result["stream_name"] = output.get("name", "stdout")
        result["size"] = len(text)
        result["preview"] = text.split('\n')[:5]
        result["description"] = [f"Text output ({len(text)} characters)"]

    elif output_type == "execute_result":
        data = output.get("data", {})
        result["data_types"] = list(data.keys())

        if "text/plain" in data:
            text = data["text/plain"]
            result["preview"] = text.split('\n')[:5]
            result["size"] = len(text)

            # Try to identify the type
            if text.startswith("<") and "DataFrame" in text:
                result["description"] = ["Pandas DataFrame"]
            elif "array(" in text:
                result["description"] = ["NumPy array"]
            else:
                result["description"] = [f"Python object ({len(text)} chars)"]

        if "text/html" in data:
            html = data["text/html"]
            result["description"] = _describe_html(html)

        if "image/png" in data or "image/jpeg" in data:
            result["description"] = _describe_image(data)

    elif output_type == "display_data":
        data = output.get("data", {})
        result["data_types"] = list(data.keys())

        if "image/png" in data:
            result["description"] = _describe_image(data)
        elif "text/html" in data:
            result["description"] = _describe_html(data.get("text/html", ""))
        else:
            result["description"] = ["Display output"]

    elif output_type == "error":
        result["error_name"] = output.get("ename", "Error")
        result["error_value"] = output.get("evalue", "")
        result["description"] = [
            f"{result['error_name']}: {result['error_value']}"
        ]

    return result


def _describe_html(html: str) -> list[str]:
    """Describe HTML output."""
    description = []

    if "<table" in html.lower():
        # Count rows
        row_count = html.lower().count("<tr")
        col_count = html.lower().count("<th")
        if col_count == 0:
            # Estimate from first row
            first_row = html.lower().split("<tr")[1] if "<tr" in html.lower() else ""
            col_count = first_row.count("<td")

        description.append(f"HTML table (~{row_count} rows, ~{col_count} columns)")

    elif "<div" in html.lower():
        description.append("HTML div content")

    else:
        description.append(f"HTML output ({len(html)} chars)")

    return description


def _describe_image(data: dict[str, Any]) -> list[str]:
    """Describe image output."""
    description = []

    if "image/png" in data:
        # Base64 encoded PNG
        png_data = data["image/png"]
        size = len(png_data) * 3 // 4  # Approximate decoded size
        description.append(f"PNG image (~{format_bytes(size)})")

        # Try to identify matplotlib figures
        description.append("Likely a matplotlib figure")

    elif "image/jpeg" in data:
        jpeg_data = data["image/jpeg"]
        size = len(jpeg_data) * 3 // 4
        description.append(f"JPEG image (~{format_bytes(size)})")

    return description

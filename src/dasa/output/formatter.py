"""LLM-friendly output formatting."""

from typing import Any, Optional


def format_bytes(size: int) -> str:
    """Format byte size for display."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def format_error(
    error_type: str,
    error_msg: str,
    line_number: Optional[int] = None,
    line_content: Optional[str] = None,
    suggestion: Optional[str] = None,
    available: Optional[list[str]] = None
) -> str:
    """Format an error with helpful context."""

    lines = [f"Error: {error_type}: {error_msg}"]

    if line_number and line_content:
        lines.append("")
        lines.append(f"Line {line_number}: {line_content}")

    if available:
        lines.append("")
        lines.append(f"Available: {', '.join(available)}")

    if suggestion:
        lines.append("")
        lines.append(f"Suggestion: {suggestion}")

    return "\n".join(lines)


def format_cell_header(index: int, cell_type: str, preview: str) -> str:
    """Format a cell header."""
    return f"[{index}] {cell_type}: {preview}"


def format_execution_result(
    cell_index: int,
    success: bool,
    elapsed: float,
    stdout: str = "",
    stderr: str = "",
    error: Optional[str] = None
) -> str:
    """Format execution result."""

    status = "OK" if success else "FAILED"
    lines = [f"Cell {cell_index}: {status} ({elapsed:.2f}s)"]

    if stdout:
        lines.append("")
        lines.append("Output:")
        for line in stdout.strip().split('\n')[:10]:  # Limit output
            lines.append(f"  {line}")
        if stdout.count('\n') > 10:
            lines.append("  ... (truncated)")

    if stderr:
        lines.append("")
        lines.append("Stderr:")
        for line in stderr.strip().split('\n')[:5]:
            lines.append(f"  {line}")

    if error:
        lines.append("")
        lines.append(f"Error: {error}")

    return "\n".join(lines)


def format_table(headers: list[str], rows: list[list[Any]]) -> str:
    """Format data as a simple text table."""

    # Calculate column widths
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], len(str(cell)))

    # Build table
    lines = []

    # Header
    header_line = "  ".join(
        str(h).ljust(widths[i]) for i, h in enumerate(headers)
    )
    lines.append(header_line)
    lines.append("-" * len(header_line))

    # Rows
    for row in rows:
        row_line = "  ".join(
            str(cell).ljust(widths[i]) for i, cell in enumerate(row) if i < len(widths)
        )
        lines.append(row_line)

    return "\n".join(lines)


def format_diff(old: str, new: str) -> str:
    """Format a diff between old and new content."""
    old_lines = old.split('\n')
    new_lines = new.split('\n')

    lines = []
    max_lines = max(len(old_lines), len(new_lines))

    for i in range(max_lines):
        old_line = old_lines[i] if i < len(old_lines) else ""
        new_line = new_lines[i] if i < len(new_lines) else ""

        if old_line != new_line:
            if old_line:
                lines.append(f"- {old_line}")
            if new_line:
                lines.append(f"+ {new_line}")
        else:
            lines.append(f"  {old_line}")

    return "\n".join(lines)


def format_variable_info(
    name: str,
    var_type: str,
    size: Optional[str] = None,
    preview: Optional[str] = None
) -> str:
    """Format variable information."""
    parts = [f"{name}: {var_type}"]
    if size:
        parts.append(f"({size})")
    if preview:
        parts.append(f"= {preview}")
    return " ".join(parts)

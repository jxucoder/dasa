"""Build rich error context for execution failures."""

import difflib
import json
from typing import Optional

from dasa.notebook.kernel import DasaKernelManager


def build_error_context(
    error_type: str,
    error_msg: str,
    source: str,
    traceback: list[str],
    kernel: DasaKernelManager,
) -> dict:
    """Build helpful context for an execution error."""
    context = {
        "error_type": error_type,
        "error_message": error_msg,
    }

    # Extract the line that caused the error from traceback
    error_line = _extract_error_line(source, traceback)
    if error_line:
        context["error_line"] = error_line

    if error_type == "KeyError":
        # Get available DataFrame columns
        col_name = error_msg.strip("'\"")
        available = _get_available_columns(kernel, source)
        if available:
            context["available_columns"] = available
            match = _fuzzy_match(col_name, available)
            if match:
                context["suggestion"] = f"Did you mean '{match}'?"

    elif error_type == "NameError":
        # Get defined variables in kernel
        var_name = _extract_name_from_error(error_msg)
        if var_name:
            available = _get_kernel_variables(kernel)
            if available:
                context["available_variables"] = available
                match = _fuzzy_match(var_name, available)
                if match:
                    context["suggestion"] = f"Did you mean '{match}'?"

    elif error_type == "ModuleNotFoundError":
        module_name = error_msg.replace("No module named ", "").strip("'\"")
        context["suggestion"] = f"Install with: pip install {module_name}"

    elif error_type in ("TypeError", "ValueError", "AttributeError"):
        context["suggestion"] = f"Check the types and values of variables used in this cell"

    return context


def _extract_error_line(source: str, traceback: list[str]) -> Optional[dict]:
    """Extract the line number and content that caused the error."""
    lines = source.splitlines()
    # Try to find line number in traceback
    for tb_line in reversed(traceback):
        # Look for patterns like "line 3" or "----> 3"
        import re
        match = re.search(r'(?:line |---->?\s*)(\d+)', tb_line)
        if match:
            line_num = int(match.group(1))
            if 1 <= line_num <= len(lines):
                return {
                    "line_number": line_num,
                    "content": lines[line_num - 1].strip(),
                }
    return None


def _get_available_columns(kernel: DasaKernelManager, source: str) -> Optional[list[str]]:
    """Try to get available DataFrame columns from the kernel."""
    # Find DataFrame variable names in the source
    import re
    # Look for patterns like df['column'] or df["column"]
    df_refs = re.findall(r'(\w+)\[', source)

    for var_name in set(df_refs):
        code = f"""
try:
    import json as _j
    _cols = list({var_name}.columns) if hasattr({var_name}, 'columns') else []
    print(_j.dumps(_cols))
except:
    print('[]')
"""
        result = kernel.execute(code, timeout=10)
        if result.success and result.stdout.strip():
            try:
                cols = json.loads(result.stdout.strip())
                if cols:
                    return cols
            except json.JSONDecodeError:
                pass
    return None


def _get_kernel_variables(kernel: DasaKernelManager) -> Optional[list[str]]:
    """Get defined variable names from the kernel."""
    code = """
import json as _j
_vars = [v for v in dir() if not v.startswith('_')]
print(_j.dumps(_vars))
"""
    result = kernel.execute(code, timeout=10)
    if result.success and result.stdout.strip():
        try:
            return json.loads(result.stdout.strip())
        except json.JSONDecodeError:
            pass
    return None


def _extract_name_from_error(error_msg: str) -> Optional[str]:
    """Extract variable name from NameError message."""
    import re
    match = re.search(r"name '(\w+)' is not defined", error_msg)
    if match:
        return match.group(1)
    return None


def _fuzzy_match(name: str, candidates: list[str]) -> Optional[str]:
    """Find closest match for a name among candidates."""
    matches = difflib.get_close_matches(name, candidates, n=1, cutoff=0.5)
    return matches[0] if matches else None

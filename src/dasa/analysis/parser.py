"""AST-based variable extraction from Python code."""

import ast
import builtins
from dataclasses import dataclass, field


BUILTIN_NAMES = set(dir(builtins))


@dataclass
class CellAnalysis:
    """Result of analyzing a cell's source code."""
    definitions: set[str] = field(default_factory=set)
    references: set[str] = field(default_factory=set)
    imports: set[str] = field(default_factory=set)
    functions: set[str] = field(default_factory=set)
    classes: set[str] = field(default_factory=set)


def parse_cell(source: str) -> CellAnalysis:
    """Parse cell source and extract variable definitions and references."""
    # Filter out magic commands and shell commands
    lines = []
    for line in source.splitlines():
        stripped = line.strip()
        if stripped.startswith(("%", "!", "?")):
            continue
        lines.append(line)
    clean_source = "\n".join(lines)

    analysis = CellAnalysis()

    try:
        tree = ast.parse(clean_source)
    except SyntaxError:
        return analysis

    _extract_definitions(tree, analysis)
    _extract_references(tree, analysis)

    # Remove self-defined and imported names from references
    analysis.references -= analysis.definitions
    analysis.references -= analysis.imports
    analysis.references -= BUILTIN_NAMES

    return analysis


def _extract_definitions(tree: ast.Module, analysis: CellAnalysis) -> None:
    """Extract all variable definitions from the AST."""
    for node in ast.walk(tree):
        # Simple assignment: x = ...
        if isinstance(node, ast.Assign):
            for target in node.targets:
                _collect_names_from_target(target, analysis.definitions)

        # Augmented assignment: x += ...
        elif isinstance(node, ast.AugAssign):
            _collect_names_from_target(node.target, analysis.definitions)

        # Annotated assignment: x: int = ...
        elif isinstance(node, ast.AnnAssign) and node.target:
            _collect_names_from_target(node.target, analysis.definitions)

        # For loop: for x in ...
        elif isinstance(node, ast.For):
            _collect_names_from_target(node.target, analysis.definitions)

        # With statement: with ... as x
        elif isinstance(node, ast.With):
            for item in node.items:
                if item.optional_vars:
                    _collect_names_from_target(item.optional_vars, analysis.definitions)

        # Function definition
        elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            analysis.definitions.add(node.name)
            analysis.functions.add(node.name)

        # Class definition
        elif isinstance(node, ast.ClassDef):
            analysis.definitions.add(node.name)
            analysis.classes.add(node.name)

        # Import: import x
        elif isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname if alias.asname else alias.name.split(".")[0]
                analysis.imports.add(name)
                analysis.definitions.add(name)

        # From import: from x import y
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == "*":
                    continue
                name = alias.asname if alias.asname else alias.name
                analysis.imports.add(name)
                analysis.definitions.add(name)

        # Named expression (walrus): x := ...
        elif isinstance(node, ast.NamedExpr):
            _collect_names_from_target(node.target, analysis.definitions)

        # Comprehension variables
        elif isinstance(node, (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)):
            for generator in node.generators:
                _collect_names_from_target(generator.target, analysis.definitions)


def _extract_references(tree: ast.Module, analysis: CellAnalysis) -> None:
    """Extract all variable references from the AST."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            analysis.references.add(node.id)


def _collect_names_from_target(target: ast.AST, names: set[str]) -> None:
    """Collect variable names from assignment targets (handles tuple unpacking)."""
    if isinstance(target, ast.Name):
        names.add(target.id)
    elif isinstance(target, (ast.Tuple, ast.List)):
        for elt in target.elts:
            _collect_names_from_target(elt, names)
    elif isinstance(target, ast.Starred):
        _collect_names_from_target(target.value, names)

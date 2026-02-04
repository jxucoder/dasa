"""Python AST parsing for variable extraction."""

import ast
import builtins
from dataclasses import dataclass, field


@dataclass
class CellAnalysis:
    """Analysis results for a code cell."""
    definitions: set[str] = field(default_factory=set)
    references: set[str] = field(default_factory=set)
    imports: set[str] = field(default_factory=set)
    functions: set[str] = field(default_factory=set)
    classes: set[str] = field(default_factory=set)


class VariableVisitor(ast.NodeVisitor):
    """AST visitor to extract variable definitions and references."""

    def __init__(self) -> None:
        self.definitions: set[str] = set()
        self.references: set[str] = set()
        self.imports: set[str] = set()
        self.functions: set[str] = set()
        self.classes: set[str] = set()
        self._scope_stack: list[set[str]] = [set()]

    def visit_Name(self, node: ast.Name) -> None:
        """Visit a Name node (variable reference or assignment target)."""
        if isinstance(node.ctx, ast.Store):
            self.definitions.add(node.id)
            self._scope_stack[-1].add(node.id)
        elif isinstance(node.ctx, ast.Load):
            # Only count as reference if not defined in current scope
            if node.id not in self._scope_stack[-1]:
                self.references.add(node.id)
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        """Visit import statement."""
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name.split('.')[0]
            self.imports.add(name)
            self.definitions.add(name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Visit from ... import statement."""
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            if name == '*':
                continue  # Can't track star imports
            self.imports.add(name)
            self.definitions.add(name)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definition."""
        self.functions.add(node.name)
        self.definitions.add(node.name)

        # Enter new scope for function body
        self._scope_stack.append(set())

        # Add parameters to local scope
        for arg in node.args.args:
            self._scope_stack[-1].add(arg.arg)

        self.generic_visit(node)
        self._scope_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function definition."""
        self.functions.add(node.name)
        self.definitions.add(node.name)

        self._scope_stack.append(set())
        for arg in node.args.args:
            self._scope_stack[-1].add(arg.arg)
        self.generic_visit(node)
        self._scope_stack.pop()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definition."""
        self.classes.add(node.name)
        self.definitions.add(node.name)

        self._scope_stack.append(set())
        self.generic_visit(node)
        self._scope_stack.pop()

    def visit_For(self, node: ast.For) -> None:
        """Visit for loop (loop variable is defined)."""
        self._visit_target(node.target)
        self.generic_visit(node)

    def visit_comprehension(self, node: ast.comprehension) -> None:
        """Visit comprehension (loop variable is local)."""
        # Comprehension variables should be local
        self._scope_stack.append(set())
        self._visit_target(node.target)
        self.generic_visit(node)
        self._scope_stack.pop()

    def visit_NamedExpr(self, node: ast.NamedExpr) -> None:
        """Visit walrus operator (:=)."""
        self.definitions.add(node.target.id)
        self.generic_visit(node)

    def _visit_target(self, target: ast.AST) -> None:
        """Extract names from assignment target."""
        if isinstance(target, ast.Name):
            self.definitions.add(target.id)
            self._scope_stack[-1].add(target.id)
        elif isinstance(target, (ast.Tuple, ast.List)):
            for elt in target.elts:
                self._visit_target(elt)


def parse_cell(source: str) -> CellAnalysis:
    """Parse a cell's source code and extract variable info."""

    # Skip magic commands and shell commands
    lines = []
    for line in source.split('\n'):
        stripped = line.strip()
        if stripped.startswith('%') or stripped.startswith('!'):
            continue
        lines.append(line)

    clean_source = '\n'.join(lines)

    try:
        tree = ast.parse(clean_source)
    except SyntaxError:
        # If we can't parse, return empty analysis
        return CellAnalysis()

    visitor = VariableVisitor()
    visitor.visit(tree)

    # Remove builtins from references
    builtin_names = set(dir(builtins))
    references = visitor.references - builtin_names - visitor.definitions

    return CellAnalysis(
        definitions=visitor.definitions,
        references=references,
        imports=visitor.imports,
        functions=visitor.functions,
        classes=visitor.classes
    )

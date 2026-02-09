"""Tests for AST parser."""

from dasa.analysis.parser import parse_cell


class TestParseCell:
    def test_simple_assignment(self):
        result = parse_cell("x = 1")
        assert "x" in result.definitions
        assert "x" not in result.references

    def test_reference(self):
        result = parse_cell("print(x)")
        assert "x" in result.references

    def test_import(self):
        result = parse_cell("import pandas as pd")
        assert "pd" in result.imports
        assert "pd" in result.definitions

    def test_from_import(self):
        result = parse_cell("from os.path import join")
        assert "join" in result.imports

    def test_function_def(self):
        result = parse_cell("def foo(x):\n    return x + 1")
        assert "foo" in result.functions
        assert "foo" in result.definitions

    def test_class_def(self):
        result = parse_cell("class MyClass:\n    pass")
        assert "MyClass" in result.classes

    def test_tuple_unpacking(self):
        result = parse_cell("a, b = 1, 2")
        assert "a" in result.definitions
        assert "b" in result.definitions

    def test_for_loop(self):
        result = parse_cell("for i in range(10):\n    print(i)")
        assert "i" in result.definitions

    def test_magic_commands_filtered(self):
        result = parse_cell("%matplotlib inline\nx = 1")
        assert "x" in result.definitions

    def test_mixed_defs_and_refs(self):
        result = parse_cell("y = x + 1")
        assert "y" in result.definitions
        assert "x" in result.references

    def test_augmented_assignment(self):
        result = parse_cell("x += 1")
        assert "x" in result.definitions

    def test_self_defined_not_in_refs(self):
        result = parse_cell("x = 1\nprint(x)")
        assert "x" in result.definitions
        assert "x" not in result.references

    def test_syntax_error_returns_empty(self):
        result = parse_cell("def (invalid")
        assert len(result.definitions) == 0
        assert len(result.references) == 0

    def test_builtins_not_in_refs(self):
        result = parse_cell("x = len([1, 2, 3])")
        assert "len" not in result.references
        assert "x" in result.definitions

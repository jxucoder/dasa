"""Tests for AST parser."""

import pytest
from dasa.analysis.parser import parse_cell


def test_parse_simple_assignment():
    """Test parsing simple assignment."""
    analysis = parse_cell("x = 1")
    assert "x" in analysis.definitions
    assert len(analysis.references) == 0


def test_parse_references():
    """Test parsing references."""
    analysis = parse_cell("y = x + 1")
    assert "y" in analysis.definitions
    assert "x" in analysis.references


def test_parse_import():
    """Test parsing imports."""
    analysis = parse_cell("import pandas as pd")
    assert "pd" in analysis.definitions
    assert "pd" in analysis.imports


def test_parse_from_import():
    """Test parsing from imports."""
    analysis = parse_cell("from pathlib import Path")
    assert "Path" in analysis.definitions
    assert "Path" in analysis.imports


def test_parse_function_def():
    """Test parsing function definitions."""
    analysis = parse_cell("def foo(x):\n    return x + 1")
    assert "foo" in analysis.definitions
    assert "foo" in analysis.functions
    assert "x" not in analysis.references  # parameter, not reference


def test_parse_class_def():
    """Test parsing class definitions."""
    analysis = parse_cell("class MyClass:\n    pass")
    assert "MyClass" in analysis.definitions
    assert "MyClass" in analysis.classes


def test_parse_magic_commands():
    """Test that magic commands are skipped."""
    analysis = parse_cell("%matplotlib inline\nx = 1")
    assert "x" in analysis.definitions


def test_parse_shell_commands():
    """Test that shell commands are skipped."""
    analysis = parse_cell("!pip install pandas\nx = 1")
    assert "x" in analysis.definitions


def test_parse_syntax_error():
    """Test handling syntax errors."""
    analysis = parse_cell("def broken(")
    # Should return empty analysis on syntax error
    assert len(analysis.definitions) == 0

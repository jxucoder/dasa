"""Test fixtures and configuration."""

import pytest
from pathlib import Path


@pytest.fixture
def eval_dir():
    """Path to evaluation directory."""
    return Path(__file__).parent.parent / "eval"


@pytest.fixture
def notebooks_dir(eval_dir):
    """Path to test notebooks."""
    return eval_dir / "notebooks"


@pytest.fixture
def clean_notebook(notebooks_dir):
    """Path to clean test notebook."""
    return str(notebooks_dir / "clean.ipynb")


@pytest.fixture
def messy_notebook(notebooks_dir):
    """Path to messy test notebook."""
    return str(notebooks_dir / "messy.ipynb")


@pytest.fixture
def broken_notebook(notebooks_dir):
    """Path to broken test notebook."""
    return str(notebooks_dir / "broken.ipynb")

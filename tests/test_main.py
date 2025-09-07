"""Tests for the main SCP MCP module."""

import pytest

from scp_mcp import __version__
from scp_mcp.main import main


def test_version():
    """Test that version is defined."""
    assert __version__ is not None
    assert isinstance(__version__, str)


def test_main_import():
    """Test that main function can be imported."""
    assert callable(main)

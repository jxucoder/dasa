"""Tests for MCP server."""

import pytest
from dasa.mcp.server import DASAServer, create_server


def test_create_server():
    """Test creating MCP server."""
    server = create_server()
    assert server is not None
    assert server.name == "dasa"


def test_server_has_tools():
    """Test server exposes tools."""
    server = create_server()
    tools = server.get_tools()

    assert isinstance(tools, list)
    assert len(tools) > 0


def test_server_has_profile_tool():
    """Test server has profile tool."""
    server = create_server()
    tools = server.get_tools()
    tool_names = [t["name"] for t in tools]

    assert "profile" in tool_names


def test_server_has_validate_tool():
    """Test server has validate tool."""
    server = create_server()
    tools = server.get_tools()
    tool_names = [t["name"] for t in tools]

    assert "validate" in tool_names


def test_server_has_deps_tool():
    """Test server has deps tool."""
    server = create_server()
    tools = server.get_tools()
    tool_names = [t["name"] for t in tools]

    assert "deps" in tool_names


def test_server_has_run_tool():
    """Test server has run tool."""
    server = create_server()
    tools = server.get_tools()
    tool_names = [t["name"] for t in tools]

    assert "run" in tool_names


def test_server_has_replay_tool():
    """Test server has replay tool."""
    server = create_server()
    tools = server.get_tools()
    tool_names = [t["name"] for t in tools]

    assert "replay" in tool_names


def test_tool_has_description():
    """Test each tool has a description."""
    server = create_server()
    tools = server.get_tools()

    for tool in tools:
        assert "description" in tool
        assert len(tool["description"]) > 0


def test_tool_has_input_schema():
    """Test each tool has an input schema."""
    server = create_server()
    tools = server.get_tools()

    for tool in tools:
        assert "inputSchema" in tool
        assert "type" in tool["inputSchema"]


@pytest.mark.asyncio
async def test_call_invalid_tool():
    """Test calling invalid tool returns error."""
    server = create_server()

    result = await server.call_tool("nonexistent", {})
    assert "error" in result

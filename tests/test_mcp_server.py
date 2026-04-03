"""Smoke tests for MCP server wiring (optional dependency ``mcp``)."""
from __future__ import annotations

import pytest

pytest.importorskip("mcp")


def test_fastmcp_import():
    from mcp.server.fastmcp import FastMCP

    assert FastMCP is not None


def test_mcp_server_module_importable():
    import mcp_server.server as srv  # noqa: F401

    assert getattr(srv, "mcp", None) is not None
    assert getattr(srv, "run_mcp_server", None) is not None

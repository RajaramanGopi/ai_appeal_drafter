"""
Model Context Protocol (MCP) server for Appeal Drafter AI.

Run with ``python -m mcp_server`` (stdio transport). See ``docs/MCP.md`` for Cursor setup.

**PHI warning:** Tools accept claim and clinical fields. Do not expose this server on a network
without host-level access control; treat connected MCP clients as trusted for PHI handling.
"""

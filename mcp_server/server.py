"""
server.py — MacroMarket MCP server entry point.

Exposes the Gold layer to MCP clients (e.g. Claude Desktop) as a small set of
read-only, typed tools. Each tool's function signature + docstring becomes the
schema the LLM sees; the LLM calls a tool by name with arguments, we run a
parameterized query as the REPORTER role, and return structured data.

Run locally:   python server.py        (stdio transport — what Claude Desktop uses)
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from tools import (
    asset_comparison,
    macro_impact,
    market_snapshot,
    regime_analysis,
    sector_performance,
)

# The server identity advertised to MCP clients.
mcp = FastMCP("macromarket")

# Register every tool module onto the server.
for module in (
    market_snapshot,
    sector_performance,
    macro_impact,
    asset_comparison,
    regime_analysis,
):
    module.register(mcp)


if __name__ == "__main__":
    # Default transport is stdio: the client launches this process and speaks
    # MCP over stdin/stdout.
    mcp.run()

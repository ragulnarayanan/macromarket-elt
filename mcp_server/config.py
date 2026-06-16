"""
config.py — connection settings for the MCP server.

The server connects as the REPORTER role (Gold-only, read-only) — the least-
privilege identity in our RBAC design. Credentials come from environment
variables: set by Claude Desktop's mcpServers config in production, or loaded
from the repo-root .env for local development.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load the repo-root .env (this file is mcp_server/config.py -> repo is parent[1]).
# In Claude Desktop, env vars are injected by the client config and take priority.
load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def get_connection_params() -> dict[str, str]:
    """Snowflake connection kwargs for the REPORTER role (Gold read-only)."""
    try:
        return {
            "account": os.environ["SF_ACCOUNT"],
            "user": os.environ["SF_USER"],
            "password": os.environ["SF_PASSWORD"],
            # REPORTER + REPORTER_WH by default — never the write roles.
            "role": os.environ.get("MCP_SF_ROLE", "REPORTER"),
            "warehouse": os.environ.get("MCP_SF_WAREHOUSE", "REPORTER_WH"),
            "database": os.environ.get("SF_DATABASE", "MACROMARKET"),
            "schema": "GOLD",
        }
    except KeyError as e:
        raise RuntimeError(
            f"Missing required env var {e}. Set SF_ACCOUNT/SF_USER/SF_PASSWORD "
            "(in .env locally, or Claude Desktop's mcpServers env block)."
        ) from e

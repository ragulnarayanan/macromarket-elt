"""
snowflake_client.py — thin Snowflake access layer for the MCP tools.

Provides a lazily-created, reused connection (the server is long-running, so we
don't reconnect per call) and a query() helper that returns rows as dicts.

SECURITY: all queries are PARAMETERIZED (%s placeholders + bound values), so user-
supplied tool arguments can never be concatenated into SQL. Combined with the
REPORTER role (Gold read-only), the LLM can't reach raw data or mutate anything.
"""

from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Any

import snowflake.connector

from config import get_connection_params


def _jsonable(value: Any) -> Any:
    """Coerce Snowflake types into JSON-serializable ones for MCP responses."""
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    return value


class SnowflakeClient:
    def __init__(self) -> None:
        self._conn = None

    def _connection(self):
        # Lazy connect; reconnect if a prior connection was closed/expired.
        if self._conn is None or self._conn.is_closed():
            self._conn = snowflake.connector.connect(**get_connection_params())
        return self._conn

    def query(self, sql: str, params: tuple | None = None) -> list[dict[str, Any]]:
        """Run a parameterized SELECT and return rows as a list of dicts."""
        cur = self._connection().cursor(snowflake.connector.DictCursor)
        try:
            cur.execute(sql, params or ())
            return [{k: _jsonable(v) for k, v in row.items()} for row in cur.fetchall()]
        finally:
            cur.close()


# Module-level singleton so every tool shares one connection.
_client: SnowflakeClient | None = None


def get_client() -> SnowflakeClient:
    global _client
    if _client is None:
        _client = SnowflakeClient()
    return _client

"""
db.py — Snowflake access for the dashboard.

Connects as the REPORTER role (Gold-only, read-only) — same least-privilege
identity as the MCP server. Credentials come from the repo-root .env locally
(in a deployed app they'd be Streamlit secrets / env vars).

Caching: the connection is cached as a resource (one per session); query results
are cached for 10 minutes so re-renders don't re-hit Snowflake.
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import snowflake.connector
import streamlit as st
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


@st.cache_resource
def _connection():
    return snowflake.connector.connect(
        account=os.environ["SF_ACCOUNT"],
        user=os.environ["SF_USER"],
        password=os.environ["SF_PASSWORD"],
        role=os.environ.get("MCP_SF_ROLE", "REPORTER"),
        warehouse=os.environ.get("MCP_SF_WAREHOUSE", "REPORTER_WH"),
        database="MACROMARKET",
        schema="GOLD",
    )


@st.cache_data(ttl=600)
def run_query(sql: str) -> pd.DataFrame:
    """Run a read-only query and return a DataFrame (columns UPPER-cased)."""
    cur = _connection().cursor(snowflake.connector.DictCursor)
    try:
        cur.execute(sql)
        return pd.DataFrame(cur.fetchall())
    finally:
        cur.close()

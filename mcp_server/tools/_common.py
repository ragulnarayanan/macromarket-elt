"""Shared helpers for MCP tools."""

from __future__ import annotations

# Map a human period code to a day count. Controlled vocabulary (never inlined
# from raw user text into SQL), with a 30-day default for unknown inputs.
_PERIOD_DAYS = {"1W": 7, "1M": 30, "3M": 90, "6M": 180, "1Y": 365, "YTD": 365}


def period_to_days(period: str) -> int:
    """Convert a period code ('1W'/'1M'/'3M'/'6M'/'1Y') to a number of days."""
    return _PERIOD_DAYS.get(period.upper(), 30)

"""get_market_snapshot — full daily market picture from fct_daily_market_snapshot."""

from __future__ import annotations

from db.snowflake_client import get_client


def get_market_snapshot(date: str = "latest") -> dict:
    """Get a full market snapshot for one trading day: S&P 500 / Nasdaq / Dow levels
    and returns, market breadth (advancers vs decliners), Bitcoin price + dominance,
    the CNN Fear & Greed reading, key macro indicators (Fed funds, 10Y/2Y Treasury,
    VIX, WTI crude), and the 10Y-2Y yield-curve spread + inversion flag.

    Args:
        date: 'latest' (default) for the most recent trading day, or 'YYYY-MM-DD'.
    """
    client = get_client()
    if date == "latest":
        rows = client.query(
            "SELECT * FROM MACROMARKET.GOLD.fct_daily_market_snapshot "
            "ORDER BY snapshot_date DESC LIMIT 1"
        )
    else:
        rows = client.query(
            "SELECT * FROM MACROMARKET.GOLD.fct_daily_market_snapshot "
            "WHERE snapshot_date = %s",
            (date,),
        )
    if not rows:
        return {"error": f"No market snapshot found for date={date!r}."}
    return rows[0]


def register(mcp) -> None:
    mcp.tool()(get_market_snapshot)

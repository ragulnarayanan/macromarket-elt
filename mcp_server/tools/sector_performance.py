"""get_sector_performance — sector returns over a period from fct_sector_performance."""

from __future__ import annotations

from db.snowflake_client import get_client
from tools._common import period_to_days


def get_sector_performance(sector: str, period: str = "1M") -> dict:
    """Get a sector's daily performance over a recent period.

    Returns the average daily return, best/worst day, number of trading days, and
    the daily series for the sector. Sector matching is fuzzy (e.g. 'tech' matches
    'Information Technology').

    Args:
        sector: GICS sector name or fragment (e.g. 'Technology', 'Energy', 'tech').
        period: one of '1W', '1M' (default), '3M', '6M', '1Y'.
    """
    client = get_client()
    days = period_to_days(period)
    rows = client.query(
        """
        SELECT gics_sector, price_date, avg_daily_return, num_constituents
        FROM MACROMARKET.GOLD.fct_sector_performance
        WHERE gics_sector ILIKE %s
          AND price_date >= DATEADD('day', %s, CURRENT_DATE())
        ORDER BY price_date
        """,
        (f"%{sector}%", -days),
    )
    if not rows:
        return {"error": f"No sector data for sector~{sector!r} in the last {period}."}

    returns = [r["AVG_DAILY_RETURN"] for r in rows if r["AVG_DAILY_RETURN"] is not None]
    best = max(rows, key=lambda r: r["AVG_DAILY_RETURN"] or -9e9)
    worst = min(rows, key=lambda r: r["AVG_DAILY_RETURN"] or 9e9)
    return {
        "sector": rows[0]["GICS_SECTOR"],
        "period": period,
        "num_days": len(rows),
        "avg_daily_return": (sum(returns) / len(returns)) if returns else None,
        "best_day": {"date": best["PRICE_DATE"], "return": best["AVG_DAILY_RETURN"]},
        "worst_day": {"date": worst["PRICE_DATE"], "return": worst["AVG_DAILY_RETURN"]},
        "daily_series": rows,
    }


def register(mcp) -> None:
    mcp.tool()(get_sector_performance)

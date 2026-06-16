"""compare_assets — side-by-side comparison of assets over a period."""

from __future__ import annotations

import statistics
from collections import defaultdict

from db.snowflake_client import get_client
from tools._common import period_to_days


def compare_assets(assets: list[str], metric: str = "returns", period: str = "3M") -> dict:
    """Compare multiple assets (stocks and/or crypto) side by side over a period.

    For each asset returns cumulative return, latest close, average daily return,
    and volatility (stddev of daily returns). Works across asset types via the
    Gold per-asset fact.

    Args:
        assets: tickers and/or coin ids, e.g. ['AAPL', 'NVDA', 'bitcoin'].
        metric: 'returns' (default) — reserved for future metrics.
        period: one of '1W', '1M', '3M' (default), '6M', '1Y'.
    """
    if not assets:
        return {"error": "Provide at least one asset, e.g. ['AAPL', 'bitcoin']."}

    client = get_client()
    days = period_to_days(period)
    keys = [a.upper() for a in assets]
    ph = ",".join(["%s"] * len(keys))
    rows = client.query(
        f"""
        SELECT asset_id, asset_name, asset_type, price_date, close, daily_return
        FROM MACROMARKET.GOLD.fct_asset_prices
        WHERE (UPPER(asset_id) IN ({ph}) OR UPPER(asset_name) IN ({ph}))
          AND price_date >= DATEADD('day', %s, CURRENT_DATE())
        ORDER BY asset_id, price_date
        """,
        tuple(keys) + tuple(keys) + (-days,),
    )
    if not rows:
        return {"error": f"No data for {assets} in the last {period}."}

    # group rows by asset
    by_asset: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_asset[r["ASSET_ID"]].append(r)

    comparison = []
    for asset_id, series in by_asset.items():
        closes = [s["CLOSE"] for s in series if s["CLOSE"] is not None]
        rets = [s["DAILY_RETURN"] for s in series if s["DAILY_RETURN"] is not None]
        cumulative = (closes[-1] / closes[0] - 1) if len(closes) >= 2 else None
        comparison.append({
            "asset_id": asset_id,
            "asset_name": series[0]["ASSET_NAME"],
            "asset_type": series[0]["ASSET_TYPE"],
            "num_days": len(series),
            "latest_close": closes[-1] if closes else None,
            "cumulative_return": cumulative,
            "avg_daily_return": (sum(rets) / len(rets)) if rets else None,
            "volatility": statistics.pstdev(rets) if len(rets) >= 2 else None,
        })

    # rank best-to-worst by cumulative return when available
    comparison.sort(key=lambda c: (c["cumulative_return"] is None, -(c["cumulative_return"] or 0)))
    return {"period": period, "metric": metric, "assets": comparison}


def register(mcp) -> None:
    mcp.tool()(compare_assets)

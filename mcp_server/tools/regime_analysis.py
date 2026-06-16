"""get_regime_analysis — average asset returns per macro regime."""

from __future__ import annotations

from db.snowflake_client import get_client


def get_regime_analysis(indicator: str = "fed_funds_rate") -> dict:
    """Get average asset returns grouped by macro regime, from fct_regime_analysis.

    Regimes combine a rate axis (Hiking / Cutting / Holding, from the Fed funds
    trend) and a volatility axis (High Vol / Low Vol, from VIX). For each combo it
    returns the number of days observed and the average S&P 500 and BTC returns —
    i.e. "how did markets behave while the Fed was hiking in a high-vol regime?"

    Args:
        indicator: informational; the current model keys on Fed funds + VIX.
    """
    client = get_client()
    rows = client.query(
        """
        SELECT rate_regime, vol_regime, num_days, avg_sp500_return, avg_btc_return
        FROM MACROMARKET.GOLD.fct_regime_analysis
        ORDER BY rate_regime, vol_regime
        """
    )
    if not rows:
        return {"error": "No regime data available."}
    return {"indicator": indicator, "regimes": rows}


def register(mcp) -> None:
    mcp.tool()(get_regime_analysis)

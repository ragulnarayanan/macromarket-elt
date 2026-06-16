"""get_macro_impact — correlation between a macro indicator and an asset."""

from __future__ import annotations

from db.snowflake_client import get_client


def get_macro_impact(indicator: str, asset: str = "SP500", lookback_months: int = 12) -> dict:
    """Get the historical correlation between a macro indicator and an asset's returns,
    from fct_macro_asset_correlation (Pearson correlation over overlapping days).

    Args:
        indicator: macro indicator (e.g. 'VIX', 'TREASURY_10Y', 'TREASURY_2Y',
                   'FED_FUNDS_RATE', 'WTI_CRUDE_OIL'). Fuzzy match.
        asset: 'SP500' (default) or 'BTC'. Fuzzy match.
        lookback_months: informational; correlations use all available history.
    """
    client = get_client()
    rows = client.query(
        """
        SELECT asset, macro_indicator, correlation, n_obs
        FROM MACROMARKET.GOLD.fct_macro_asset_correlation
        WHERE asset ILIKE %s AND macro_indicator ILIKE %s
        """,
        (f"%{asset}%", f"%{indicator}%"),
    )
    if not rows:
        return {"error": f"No correlation found for asset~{asset!r}, indicator~{indicator!r}."}

    r = rows[0]
    corr = r["CORRELATION"]
    # plain-language reading of the coefficient for the LLM/user
    if corr is None:
        strength = "insufficient overlapping data to compute"
    else:
        a = abs(corr)
        mag = "strong" if a >= 0.6 else "moderate" if a >= 0.3 else "weak"
        direction = "positive" if corr > 0 else "negative"
        strength = f"{mag} {direction} correlation"
    return {
        "asset": r["ASSET"],
        "macro_indicator": r["MACRO_INDICATOR"],
        "correlation": corr,
        "n_obs": r["N_OBS"],
        "interpretation": strength,
    }


def register(mcp) -> None:
    mcp.tool()(get_macro_impact)

# MCP Server — Demo Transcript

Real responses from the MacroMarket MCP server (connected to Snowflake **Gold** as the
read-only `REPORTER` role). In Claude Desktop these tools are called automatically from
natural-language questions; below, each example shows the question, the tool invoked, and
the (lightly trimmed) JSON returned. See `mcp_server/` for the implementation.

---

### "What's today's market snapshot?"
→ `get_market_snapshot()`
```json
{
  "SNAPSHOT_DATE": "2026-06-16",
  "SP500_CLOSE": 7526.16, "SP500_RETURN": -0.0037,
  "NASDAQ_CLOSE": 26483.96, "DOW_CLOSE": 52116.33,
  "ADVANCERS": 5, "DECLINERS": 5,
  "BTC_PRICE": 65624.16, "BTC_DOMINANCE": 61.42, "BTC_RETURN": -0.0084,
  "FNG_VALUE": 23, "FNG_CLASSIFICATION": "Extreme Fear"
}
```

### "Compare AAPL, NVDA, and Bitcoin over the last month."
→ `compare_assets(["AAPL","NVDA","bitcoin"], period="1M")`
```json
{
  "period": "1M",
  "assets": [
    {"asset_id": "AAPL",    "cumulative_return":  0.0068, "volatility": 0.0152},
    {"asset_id": "bitcoin", "cumulative_return": -0.1579, "volatility": 0.0211},
    {"asset_id": "NVDA",    "cumulative_return": -0.0599, "volatility": 0.0267}
  ]
}
```

### "How correlated is Bitcoin with the VIX?"
→ `get_macro_impact("VIX", "BTC")`
```json
{
  "asset": "BTC", "macro_indicator": "VIX",
  "correlation": 0.189, "n_obs": 20,
  "interpretation": "weak positive correlation"
}
```

### "How has the Technology sector done this month?"
→ `get_sector_performance("Technology", "1M")`
```json
{
  "sector": "Information Technology", "period": "1M", "num_days": 21,
  "avg_daily_return": -0.0020,
  "best_day":  {"date": "2026-06-15", "return":  0.0255},
  "worst_day": {"date": "2026-06-05", "return": -0.0337}
}
```

### "How do markets behave across Fed rate regimes?"
→ `get_regime_analysis()`
```json
{
  "regimes": [
    {"RATE_REGIME": "Holding", "VOL_REGIME": "Low Vol",  "NUM_DAYS": 18, "AVG_SP500_RETURN":  0.0032, "AVG_BTC_RETURN": -0.0103},
    {"RATE_REGIME": "Holding", "VOL_REGIME": "High Vol", "NUM_DAYS":  2, "AVG_SP500_RETURN": -0.0213, "AVG_BTC_RETURN": -0.0181},
    {"RATE_REGIME": "Cutting", "VOL_REGIME": "Low Vol",  "NUM_DAYS":  1, "AVG_SP500_RETURN":  0.0061, "AVG_BTC_RETURN": -0.0189}
  ]
}
```

---

**Governance:** every tool runs a parameterized query as `REPORTER` (Gold-only, read-only).
The LLM never writes SQL and cannot reach Bronze/Silver or mutate anything.

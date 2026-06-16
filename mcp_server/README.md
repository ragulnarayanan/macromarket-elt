# MacroMarket MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) server that exposes the
Snowflake **Gold** layer to LLMs (e.g. Claude Desktop) as governed, read-only tools.
It connects as the **`REPORTER`** role — Gold-only, read-only — so the LLM can never
write SQL, see raw data, or mutate anything. It's a *semantic access layer*, not a
database connection.

## Tools

| Tool | What it returns |
|------|-----------------|
| `get_market_snapshot(date="latest")` | Full daily snapshot: indices, breadth, BTC, Fear & Greed, macro, yield curve |
| `get_sector_performance(sector, period="1M")` | Sector daily returns over a period |
| `get_macro_impact(indicator, asset="SP500", lookback_months=12)` | Correlation between a macro indicator and an asset |
| `compare_assets(assets, metric="returns", period="3M")` | Side-by-side cumulative return / volatility for multiple assets |
| `get_regime_analysis(indicator="fed_funds_rate")` | Average asset returns per macro regime (rate trend × volatility) |

## Run locally

```bash
pip install -r mcp_server/requirements.txt
set -a; source .env; set +a          # provides REPORTER creds
cd mcp_server && python server.py    # stdio transport
```

## Use with Claude Desktop

1. Copy the `macromarket` block from `claude_desktop_config.example.json` into your
   real config (`~/Library/Application Support/Claude/claude_desktop_config.json`),
   using absolute paths and your Snowflake credentials.
2. Restart Claude Desktop.
3. Ask things like:
   - "What's today's market snapshot?"
   - "Compare AAPL, NVDA, and bitcoin over the last month."
   - "How correlated is the VIX with the S&P 500?"
   - "How do stocks perform across Fed rate regimes?"

## Architecture

```
Claude Desktop ──MCP(stdio)──> server.py ──> tools/*.py ──> db/snowflake_client.py
                                                              │ REPORTER role
                                                              ▼
                                                    Snowflake GOLD (read-only)
```

# MacroMarket Dashboard (Streamlit)

A multi-page dashboard over the Snowflake **Gold** layer, connecting as the
**`REPORTER`** role (read-only). Same data the MCP server exposes — here as charts.

## Pages

| Page | Reads | Shows |
|------|-------|-------|
| Market Overview (`app.py`) | `fct_daily_market_snapshot` | KPIs, Fear & Greed gauge, S&P trend, breadth, yield spread |
| Sector Heatmap | `fct_sector_performance` | Sector × date return heatmap + cumulative bar |
| Macro Correlations | `fct_macro_asset_correlation` | Asset × macro correlation matrix |
| Regime Analysis | `fct_regime_analysis` | Avg S&P return per macro regime |

## Run

```bash
pip install -r streamlit/requirements.txt
set -a; source .env; set +a        # provides REPORTER creds
streamlit run streamlit/app.py
```

Then open http://localhost:8501. Credentials come from the repo-root `.env` locally
(`SF_ACCOUNT`/`SF_USER`/`SF_PASSWORD`; role/warehouse default to `REPORTER`/`REPORTER_WH`).
For a deployed app, use Streamlit secrets / environment variables instead.

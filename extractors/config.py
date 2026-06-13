"""
config.py — single source of truth for the extractors.

WHAT: Defines the data "universe" (which tickers, FRED series, and coins we
      pull), local file paths, and helpers that read credentials from the
      environment (.env locally; Key Vault → env vars in production).

WHY:  Centralizing config means an extractor never hardcodes a list or a secret.
      Want more tickers? Edit STOCK_TICKERS here, nowhere else. Want to swap dev
      (10 tickers) for prod (S&P 500)? One change.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the repo root so `os.environ` has our secrets locally.
load_dotenv()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
# Repo root = two levels up from this file (extractors/config.py -> repo/).
REPO_ROOT = Path(__file__).resolve().parents[1]

# Where extractors write JSON before it's uploaded to ADLS. Gitignored (data/).
# This mirrors the ADLS layout: data/<source-subdir>/<date>.json
OUTPUT_DIR = REPO_ROOT / "data"

# ---------------------------------------------------------------------------
# Data universes — WHAT we ingest.
# Start small (dev) so test runs are fast and cheap; scale up later.
# ---------------------------------------------------------------------------

# Yahoo Finance: a 10-stock dev slice of the S&P 500. Swap for the full list
# (via seeds/sp500_tickers.csv) once the pipeline is proven end to end.
STOCK_TICKERS: list[str] = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL",
    "META", "TSLA", "JPM", "XOM", "JNJ",
]

# Major indices (the "^" prefix is Yahoo's index notation).
INDICES: list[str] = ["^GSPC", "^DJI", "^IXIC"]  # S&P 500, Dow, Nasdaq

# SPDR sector ETFs — proxies for sector performance.
SECTOR_ETFS: list[str] = [
    "XLF", "XLK", "XLE", "XLV", "XLY",
    "XLP", "XLI", "XLB", "XLRE", "XLU", "XLC",
]

# Everything Yahoo price/news extractors iterate over.
ALL_YAHOO_SYMBOLS: list[str] = STOCK_TICKERS + INDICES + SECTOR_ETFS

# FRED macroeconomic series (id -> human label, used as metadata in Bronze).
# Mirrors the spec's table in Section 3.2.
FRED_SERIES: dict[str, str] = {
    "DFF": "Federal Funds Effective Rate",
    "DGS10": "10-Year Treasury Yield",
    "DGS2": "2-Year Treasury Yield",
    "CPIAUCSL": "Consumer Price Index (CPI)",
    "GDPC1": "Real GDP",
    "UNRATE": "Unemployment Rate",
    "M2SL": "M2 Money Supply",
    "VIXCLS": "CBOE Volatility Index (VIX)",
    "DCOILWTICO": "WTI Crude Oil Price",
    "DEXUSEU": "USD/EUR Exchange Rate",
}

# CoinGecko: pull the top N coins by market cap (no fixed symbol list — the API
# ranks them for us). vs_currency = the quote currency.
CRYPTO_TOP_N: int = 20
CRYPTO_VS_CURRENCY: str = "usd"

# ---------------------------------------------------------------------------
# API endpoints + tunables
# ---------------------------------------------------------------------------
FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"
COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"
FEAR_GREED_URL = "https://api.alternative.me/fng/"

# Politeness delay (seconds) between batched API calls to respect rate limits.
REQUEST_DELAY_SECONDS = 2.0

# ---------------------------------------------------------------------------
# Credential helpers — read from env (set by .env locally, Key Vault in prod).
# Functions, not module-level constants, so importing config never crashes when
# a secret is missing; it only matters when you actually need that credential.
# ---------------------------------------------------------------------------

def get_fred_api_key() -> str | None:
    """FRED API key, or None if unset (FRED extractor skips gracefully)."""
    return os.environ.get("FRED_API_KEY")


def get_adls_connection_string() -> str:
    """ADLS Gen2 connection string. Raises if missing (upload can't proceed)."""
    try:
        return os.environ["AZURE_STORAGE_CONNECTION_STRING"]
    except KeyError as e:
        raise RuntimeError(
            "AZURE_STORAGE_CONNECTION_STRING is not set. Add it to .env "
            "(see azure/setup.sh output)."
        ) from e


def get_snowflake_config() -> dict[str, str]:
    """Snowflake connection kwargs for snowflake.connector.connect()."""
    try:
        return {
            "account": os.environ["SF_ACCOUNT"],
            "user": os.environ["SF_USER"],
            "password": os.environ["SF_PASSWORD"],
            "role": os.environ.get("SF_ROLE", "LOADER"),
            "warehouse": os.environ.get("SF_WAREHOUSE", "LOADER_WH"),
            "database": os.environ.get("SF_DATABASE", "MACROMARKET"),
        }
    except KeyError as e:
        raise RuntimeError(f"Missing Snowflake env var: {e}. Add it to .env.") from e


# The ADLS container (filesystem) all raw files live in.
ADLS_CONTAINER = "raw-data"

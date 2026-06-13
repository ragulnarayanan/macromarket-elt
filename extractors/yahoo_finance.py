"""
yahoo_finance.py — stock/index/ETF data from Yahoo Finance via the `yfinance` lib.

This source feeds TWO Bronze tables, so it has TWO extractor classes:
  • YahooPricesExtractor       -> daily OHLCV       -> stock-prices/
  • YahooFundamentalsExtractor -> market cap, P/E…  -> stock-fundamentals/

Both implement the same BaseExtractor contract, so run_all.py treats them like
any other extractor. No API key required.
"""

from __future__ import annotations

import time
from datetime import date, timedelta
from pathlib import Path

import yfinance as yf

from extractors import config
from extractors.base import BaseExtractor


class YahooPricesExtractor(BaseExtractor):
    """Daily Open/High/Low/Close/Adj-Close/Volume per symbol."""

    @property
    def source_name(self) -> str:
        return "yahoo_finance"

    @property
    def adls_subdir(self) -> str:
        return "stock-prices"

    def extract(self, start_date: date, end_date: date) -> Path:
        records: list[dict] = []
        for symbol in config.ALL_YAHOO_SYMBOLS:
            try:
                # auto_adjust=False keeps BOTH raw Close and Adj Close (splits/divs).
                # yfinance's `end` is exclusive, so add a day to include end_date.
                hist = yf.Ticker(symbol).history(
                    start=start_date.isoformat(),
                    end=(end_date + timedelta(days=1)).isoformat(),
                    auto_adjust=False,
                )
            except Exception as e:  # one bad ticker shouldn't kill the batch
                self.log.error("ticker_failed", symbol=symbol, error=str(e))
                continue

            for ts, row in hist.iterrows():
                records.append(
                    {
                        "ticker": symbol,
                        "date": ts.date().isoformat(),
                        "open": _f(row.get("Open")),
                        "high": _f(row.get("High")),
                        "low": _f(row.get("Low")),
                        "close": _f(row.get("Close")),
                        "adj_close": _f(row.get("Adj Close")),
                        "volume": _i(row.get("Volume")),
                        "source": self.source_name,
                    }
                )
            time.sleep(0.5)  # gentle pacing across symbols

        return self.save_records(records, end_date)


class YahooFundamentalsExtractor(BaseExtractor):
    """Point-in-time fundamentals: market cap, P/E, sector, industry."""

    @property
    def source_name(self) -> str:
        return "yahoo_finance"

    @property
    def adls_subdir(self) -> str:
        return "stock-fundamentals"

    def extract(self, start_date: date, end_date: date) -> Path:
        records: list[dict] = []
        # Indices (^GSPC etc.) have no fundamentals — only real tickers + ETFs.
        symbols = config.STOCK_TICKERS + config.SECTOR_ETFS
        for symbol in symbols:
            try:
                info = yf.Ticker(symbol).info  # one dict of company metadata
            except Exception as e:
                self.log.error("info_failed", symbol=symbol, error=str(e))
                continue

            records.append(
                {
                    "ticker": symbol,
                    "date": end_date.isoformat(),  # fundamentals are a snapshot
                    "market_cap": info.get("marketCap"),
                    "pe_ratio": info.get("trailingPE"),
                    "sector": info.get("sector"),
                    "industry": info.get("industry"),
                    "short_name": info.get("shortName"),
                    "source": self.source_name,
                }
            )
            time.sleep(config.REQUEST_DELAY_SECONDS)  # .info is heavier — pace it

        return self.save_records(records, end_date)


# --- tiny coercion helpers: pandas/NaN -> clean JSON-safe values -----------
def _f(v) -> float | None:
    """Float or None (NaN/missing -> None)."""
    try:
        f = float(v)
        return None if f != f else f  # f != f is True only for NaN
    except (TypeError, ValueError):
        return None


def _i(v) -> int | None:
    """Int or None."""
    f = _f(v)
    return None if f is None else int(f)

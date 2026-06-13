"""
yahoo_news.py — financial news headlines per ticker (for Databricks FinBERT).

These headlines are the INPUT to the Phase 5 sentiment enrichment: Databricks
reads them from Silver, scores each with FinBERT, and writes sentiment back to
Gold. Here we just collect the raw headlines.

yfinance has changed its `.news` payload shape across versions, so we parse
defensively (new "content" nested form AND the older flat form). No API key.
"""

from __future__ import annotations

import time
from datetime import date
from pathlib import Path
from typing import Any

import yfinance as yf

from extractors import config
from extractors.base import BaseExtractor


class YahooNewsExtractor(BaseExtractor):
    @property
    def source_name(self) -> str:
        return "yahoo_finance_news"

    @property
    def adls_subdir(self) -> str:
        return "news-headlines"

    def extract(self, start_date: date, end_date: date) -> Path:
        records: list[dict] = []
        # News only makes sense for real companies (skip indices/ETFs).
        for symbol in config.STOCK_TICKERS:
            try:
                items = yf.Ticker(symbol).news or []
            except Exception as e:
                self.log.error("news_failed", symbol=symbol, error=str(e))
                continue

            for item in items:
                parsed = self._parse_news_item(symbol, item, end_date)
                if parsed:
                    records.append(parsed)
            time.sleep(0.5)

        return self.save_records(records, end_date)

    def _parse_news_item(self, symbol: str, item: dict[str, Any], run_date: date) -> dict | None:
        """Normalize one news item across yfinance's old/new shapes."""
        # New shape (>=0.2.40-ish): fields live under item["content"].
        content = item.get("content", item)

        headline = content.get("title")
        if not headline:
            return None  # nothing useful without a headline

        # Publisher: new form nests it under provider.displayName.
        provider = content.get("provider") or {}
        publisher = (
            provider.get("displayName")
            or content.get("publisher")
            or item.get("publisher")
        )

        # Published date: new form has ISO "pubDate"; old form has a Unix int.
        published = content.get("pubDate") or item.get("providerPublishTime")

        # URL: new form nests under canonicalUrl.url; old form is "link".
        canonical = content.get("canonicalUrl") or {}
        url = canonical.get("url") or content.get("link") or item.get("link")

        return {
            "ticker": symbol,
            "headline": headline,
            "publisher": publisher,
            "published_date": str(published) if published is not None else None,
            "url": url,
            "extracted_date": run_date.isoformat(),
            "source": self.source_name,
        }

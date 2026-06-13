"""
coingecko.py — top-N cryptocurrencies by market cap from CoinGecko (free tier).

We use the /coins/markets endpoint, which ranks coins for us and returns a daily
SNAPSHOT (current price, market cap, 24h volume, supply). That's the right shape
for a daily pipeline. (Deep historical backfill would use /coins/{id}/market_chart
per coin — noted as a future enhancement.)

No API key required on the free/demo tier.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import requests

from extractors import config
from extractors.base import BaseExtractor
from extractors.utils import with_retry


class CoinGeckoExtractor(BaseExtractor):
    @property
    def source_name(self) -> str:
        return "coingecko"

    @property
    def adls_subdir(self) -> str:
        return "crypto-prices"

    @with_retry
    def _fetch_markets(self) -> list[dict]:
        """Fetch the top-N coins by market cap (one efficient call)."""
        resp = requests.get(
            f"{config.COINGECKO_BASE_URL}/coins/markets",
            params={
                "vs_currency": config.CRYPTO_VS_CURRENCY,
                "order": "market_cap_desc",     # rank by market cap, descending
                "per_page": config.CRYPTO_TOP_N,  # top N
                "page": 1,
                "sparkline": "false",
            },
            timeout=20,
        )
        resp.raise_for_status()
        return resp.json()

    def extract(self, start_date: date, end_date: date) -> Path:
        # /coins/markets is a point-in-time snapshot, so we stamp it with the
        # run date (end_date). start_date is unused for this source.
        coins = self._fetch_markets()

        records = [
            {
                "coin_id": c["id"],
                "symbol": c["symbol"],
                "name": c["name"],
                "date": end_date.isoformat(),
                "price_usd": c["current_price"],
                "market_cap": c["market_cap"],
                "total_volume": c["total_volume"],
                "circulating_supply": c["circulating_supply"],
                "market_cap_rank": c["market_cap_rank"],
                "source": self.source_name,
            }
            for c in coins
        ]

        return self.save_records(records, end_date)

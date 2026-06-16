"""
coingecko.py — top-N cryptocurrencies by market cap from CoinGecko (free tier).

We use the /coins/markets endpoint, which ranks coins for us and returns a daily
SNAPSHOT (current price, market cap, 24h volume, supply). That's the right shape
for a daily pipeline. (Deep historical backfill would use /coins/{id}/market_chart
per coin — noted as a future enhancement.)

No API key required on the free/demo tier.
"""

from __future__ import annotations

import time
from datetime import date, datetime, timezone
from pathlib import Path

import requests

from extractors import config
from extractors.base import BaseExtractor
from extractors.utils import with_retry, write_json


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

    # --- one-off historical backfill -------------------------------------
    @with_retry
    def _fetch_market_chart(self, coin_id: str, days: int) -> dict:
        """Fetch a coin's market chart (no interval param -> free-tier friendly;
        the API returns hourly points which we downsample to daily)."""
        resp = requests.get(
            f"{config.COINGECKO_BASE_URL}/coins/{coin_id}/market_chart",
            params={"vs_currency": config.CRYPTO_VS_CURRENCY, "days": days},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def extract_history(self, days: int = 30) -> Path:
        """Backfill a daily price/market-cap/volume series for the top-N coins.

        Gives crypto a real time series (the /coins/markets snapshot is a single
        point), so daily returns and BTC correlations can be computed. Writes to
        crypto-prices/history.json so it coexists with the daily snapshot files.
        """
        coins = self._fetch_markets()
        records: list[dict] = []
        for c in coins:
            # Free-tier rate limits are tight for this endpoint; skip a coin that
            # keeps 429-ing rather than failing the whole backfill.
            try:
                chart = self._fetch_market_chart(c["id"], days)
            except Exception as e:
                self.log.warning("coin_history_skipped", coin=c["id"], error=str(e))
                time.sleep(8)
                continue
            caps = {int(ts): v for ts, v in chart.get("market_caps", [])}
            vols = {int(ts): v for ts, v in chart.get("total_volumes", [])}
            # downsample to one point per date: keep the latest timestamp per day
            daily: dict[str, tuple[int, float]] = {}
            for ts, price in chart.get("prices", []):
                d = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).date().isoformat()
                if d not in daily or ts > daily[d][0]:
                    daily[d] = (int(ts), price)
            for d, (ts, price) in daily.items():
                records.append({
                    "coin_id": c["id"],
                    "symbol": c["symbol"],
                    "name": c["name"],
                    "date": d,
                    "price_usd": price,
                    "market_cap": caps.get(ts),
                    "total_volume": vols.get(ts),
                    "circulating_supply": None,
                    "market_cap_rank": c.get("market_cap_rank"),
                    "source": self.source_name,
                })
            self.log.info("coin_history", coin=c["id"], days=len(daily))
            time.sleep(8)  # stay under the free-tier rate limit

        path = config.OUTPUT_DIR / self.adls_subdir / "history.json"
        write_json(records, path)
        self.log.info("history_saved", records=len(records),
                      path=str(path.relative_to(config.REPO_ROOT)))
        return path

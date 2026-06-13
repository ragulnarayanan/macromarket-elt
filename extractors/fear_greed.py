"""
fear_greed.py — CNN Fear & Greed Index from the alternative.me API.

Smallest, simplest source — read this first to learn the extractor pattern:
  1. Build the request, 2. fetch with retry, 3. normalize to flat records,
  4. hand off to self.save_records() (defined in BaseExtractor).

No API key required.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

import requests

from extractors import config
from extractors.base import BaseExtractor
from extractors.utils import with_retry


class FearGreedExtractor(BaseExtractor):
    @property
    def source_name(self) -> str:
        return "alternative_me"

    @property
    def adls_subdir(self) -> str:
        return "fear-greed"

    @with_retry
    def _fetch(self, limit: int) -> list[dict]:
        """Fetch the last `limit` daily readings. Retries on network failure."""
        resp = requests.get(
            config.FEAR_GREED_URL,
            params={"limit": limit, "format": "json"},
            timeout=15,
        )
        resp.raise_for_status()  # turn 4xx/5xx into an exception (-> retry/fail)
        return resp.json()["data"]

    def extract(self, start_date: date, end_date: date) -> Path:
        # The API returns the most-recent N readings; ask for enough to cover
        # the requested window (+1 for inclusivity), then filter precisely.
        days = (end_date - start_date).days + 1
        raw = self._fetch(limit=max(days, 1))

        records: list[dict] = []
        for item in raw:
            # `timestamp` is Unix seconds (UTC); convert to a calendar date.
            reading_date = datetime.fromtimestamp(
                int(item["timestamp"]), tz=timezone.utc
            ).date()
            if start_date <= reading_date <= end_date:
                records.append(
                    {
                        "date": reading_date.isoformat(),
                        "value": int(item["value"]),
                        "classification": item["value_classification"],
                        "source": self.source_name,
                    }
                )

        return self.save_records(records, end_date)

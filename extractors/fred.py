"""
fred.py — macroeconomic indicators from FRED (Federal Reserve Economic Data).

Loops over the series defined in config.FRED_SERIES, fetching observations for
the date window per series. One flat record per (series, date).

API key required (free): https://fred.stlouisfed.org/docs/api/api_key.html
If FRED_API_KEY is unset, the extractor logs a warning and writes nothing — so
it never crashes the pipeline before you've added your key.
"""

from __future__ import annotations

import time
from datetime import date
from pathlib import Path

import requests

from extractors import config
from extractors.base import BaseExtractor
from extractors.utils import with_retry


class FredExtractor(BaseExtractor):
    @property
    def source_name(self) -> str:
        return "fred"

    @property
    def adls_subdir(self) -> str:
        return "fred-series"

    @with_retry
    def _fetch_series(self, series_id: str, api_key: str, start: date, end: date) -> list[dict]:
        """Fetch one series' observations over the window."""
        resp = requests.get(
            config.FRED_BASE_URL,
            params={
                "series_id": series_id,
                "api_key": api_key,
                "file_type": "json",
                "observation_start": start.isoformat(),
                "observation_end": end.isoformat(),
            },
            timeout=20,
        )
        resp.raise_for_status()
        return resp.json().get("observations", [])

    def extract(self, start_date: date, end_date: date) -> Path:
        api_key = config.get_fred_api_key()
        if not api_key:
            self.log.warning("fred_api_key_missing", action="skipping")
            return self.save_records([], end_date)

        records: list[dict] = []
        for series_id, series_name in config.FRED_SERIES.items():
            observations = self._fetch_series(series_id, api_key, start_date, end_date)
            for obs in observations:
                # FRED uses "." for a missing/unavailable value -> store as None.
                raw_value = obs.get("value")
                value = None if raw_value in (".", "", None) else float(raw_value)
                records.append(
                    {
                        "series_id": series_id,
                        "series_name": series_name,
                        "date": obs["date"],
                        "value": value,
                        "realtime_start": obs.get("realtime_start"),
                        "realtime_end": obs.get("realtime_end"),
                        "source": self.source_name,
                    }
                )
            self.log.info("series_fetched", series_id=series_id, observations=len(observations))
            time.sleep(config.REQUEST_DELAY_SECONDS)  # be polite to the API

        return self.save_records(records, end_date)

"""
base.py — the BaseExtractor abstract class every source extractor inherits.

WHY an abstract base class: it defines a CONTRACT. The orchestrator (run_all.py)
and the uploader can treat all 5 extractors identically — call .extract(),
read .adls_subdir — without caring whether the data came from Yahoo or FRED.
This is the "template method" pattern: the base owns the shared skeleton
(file naming, saving, logging); each subclass fills in only its API-specific
extraction logic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from pathlib import Path
from typing import Any

from extractors import config
from extractors.utils import get_logger, write_json


class BaseExtractor(ABC):
    """Common interface + shared behavior for all data-source extractors."""

    def __init__(self) -> None:
        # Logger tagged with this source's name (e.g. source=coingecko).
        self.log = get_logger(self.source_name)

    # --- Contract each subclass MUST implement -----------------------------
    @property
    @abstractmethod
    def source_name(self) -> str:
        """Stable identifier for this source, e.g. 'yahoo_finance'."""

    @property
    @abstractmethod
    def adls_subdir(self) -> str:
        """ADLS/local subfolder for this source's files, e.g. 'stock-prices'.

        This is the link between the extractor and the storage layout: files go
        to data/<adls_subdir>/<date>.json locally, then the SAME relative path
        in ADLS, then COPY INTO reads from @stage/<adls_subdir>/...
        """

    @abstractmethod
    def extract(self, start_date: date, end_date: date) -> Path:
        """Pull data for the date range, save it as JSON, return the file path.

        Subclasses gather records however their API works, then call
        self.save_records(records, end_date) to persist + return the path.
        """

    # --- Shared behavior every subclass reuses -----------------------------
    def save_records(self, records: list[dict[str, Any]], file_date: date) -> Path:
        """Write records to data/<adls_subdir>/<file_date>.json (idempotent).

        Date-based naming is what makes re-runs safe: running the same day twice
        overwrites that day's file rather than creating duplicates.
        """
        # Local path mirrors the ADLS layout exactly.
        path = config.OUTPUT_DIR / self.adls_subdir / f"{file_date.isoformat()}.json"

        if not records:
            # Never silently produce nothing — surface it loudly. We still write
            # an empty file so downstream steps have a consistent artifact.
            self.log.warning("no_records_extracted", file_date=str(file_date))

        write_json(records, path)
        self.log.info(
            "saved",
            records=len(records),
            path=str(path.relative_to(config.REPO_ROOT)),
        )
        return path

"""
utils.py — shared helpers for all extractors: logging, retry, dates, JSON I/O.

WHY a shared module: every extractor needs the same cross-cutting behavior
(log the same way, retry flaky calls the same way, write JSON the same way).
Putting it here keeps each extractor focused on its ONE job: talking to its API.
"""

from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import requests
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

# ---------------------------------------------------------------------------
# Logging — structured logs (key=value), easy to read locally and parse in prod.
# ---------------------------------------------------------------------------
structlog.configure(
    processors=[
        structlog.processors.add_log_level,           # adds level=info/error
        structlog.processors.TimeStamper(fmt="iso"),   # adds an ISO timestamp
        structlog.dev.ConsoleRenderer(),               # pretty, colored output
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
)


def get_logger(source: str) -> structlog.BoundLogger:
    """Return a logger pre-tagged with the source name, e.g. source=coingecko.

    Every line that logger emits carries `source=...`, so when 5 extractors run
    together you can tell at a glance which one produced which line.
    """
    return structlog.get_logger().bind(source=source)


# ---------------------------------------------------------------------------
# Retry — wrap any flaky network call so transient failures self-heal.
# ---------------------------------------------------------------------------
# Decorator usage:
#     @with_retry
#     def call_api(...): ...
#
# Behavior: up to 4 attempts, waiting 2s, 4s, 8s between tries (exponential
# backoff, capped at 30s). `reraise=True` means after the final failure the
# ORIGINAL exception propagates (so we never silently swallow a real error).
with_retry = retry(
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    # Cover both builtin network errors AND any requests-library failure
    # (timeouts, connection drops, 5xx via raise_for_status()).
    retry=retry_if_exception_type(
        (ConnectionError, TimeoutError, OSError, requests.exceptions.RequestException)
    ),
    reraise=True,
)


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------
def daterange(start: date, end: date):
    """Yield each date from start to end inclusive (used for backfills)."""
    cur = start
    while cur <= end:
        yield cur
        cur += timedelta(days=1)


def today() -> date:
    """Today's date (wrapper so call sites read clearly / are easy to mock)."""
    return date.today()


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------
def write_json(records: list[dict[str, Any]], path: Path) -> Path:
    """Write a list of records to `path` as JSON, creating parent dirs.

    We write a top-level JSON ARRAY because the Snowflake stage's file format
    uses STRIP_OUTER_ARRAY=TRUE, which turns each array element into its own
    Bronze row. So the on-disk shape here directly determines the row shape in
    Snowflake.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        # default=str safely serializes dates/Decimals/etc. that aren't native JSON.
        json.dump(records, f, default=str)
    return path

"""
run_all.py — orchestrate the full ingestion cycle.

Runs every extractor over a date window, then OPTIONALLY uploads to ADLS and
loads into Snowflake Bronze. This is the single entry point ADF will call in
production (Phase 7), and what `make extract` runs locally.

USAGE:
    python -m extractors.run_all                      # extract today -> data/
    python -m extractors.run_all --upload --load      # full extract->ADLS->Bronze
    python -m extractors.run_all --start 2026-06-01 --end 2026-06-13   # backfill

Design note: each extractor is independent, so one failing source is logged and
skipped — we never let a single bad API kill the whole run.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime

from extractors.base import BaseExtractor
from extractors.coingecko import CoinGeckoExtractor
from extractors.fear_greed import FearGreedExtractor
from extractors.fred import FredExtractor
from extractors.utils import get_logger, today
from extractors.yahoo_finance import YahooFundamentalsExtractor, YahooPricesExtractor

log = get_logger("run_all")

# The full extractor lineup. Order doesn't matter — they're independent.
EXTRACTORS: list[type[BaseExtractor]] = [
    YahooPricesExtractor,
    YahooFundamentalsExtractor,
    FredExtractor,
    CoinGeckoExtractor,
    FearGreedExtractor,
]


def _parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def run_extractors(start: date, end: date) -> None:
    """Run every extractor; log a per-source pass/fail summary."""
    log.info("extract_start", start=str(start), end=str(end), sources=len(EXTRACTORS))
    succeeded, failed = 0, 0
    for Ext in EXTRACTORS:
        name = Ext.__name__
        try:
            Ext().extract(start, end)
            succeeded += 1
        except Exception as e:
            # Isolate failures: log and continue so other sources still run.
            log.error("extractor_failed", extractor=name, error=str(e))
            failed += 1
    log.info("extract_done", succeeded=succeeded, failed=failed)


def main() -> None:
    parser = argparse.ArgumentParser(description="MacroMarket ingestion orchestrator")
    parser.add_argument("--start", type=_parse_date, help="YYYY-MM-DD (default: today)")
    parser.add_argument("--end", type=_parse_date, help="YYYY-MM-DD (default: today)")
    parser.add_argument("--upload", action="store_true", help="upload to ADLS (step 2)")
    parser.add_argument("--load", action="store_true", help="COPY INTO Bronze (step 3)")
    args = parser.parse_args()

    end = args.end or today()
    start = args.start or end

    # Step 1 — extract.
    run_extractors(start, end)

    # Step 2 — upload to ADLS (imported lazily so extract-only runs need no
    # Azure credentials configured).
    if args.upload:
        from extractors.adls_uploader import upload_all
        upload_all()

    # Step 3 — load into Snowflake Bronze.
    if args.load:
        from extractors.loader import load_all
        load_all()


if __name__ == "__main__":
    main()

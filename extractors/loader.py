"""
loader.py — STEP 3 of ingestion: ADLS -> Snowflake BRONZE via COPY INTO.

WHAT: For each source subfolder in the ADLS stage, runs a COPY INTO that loads
      the JSON into the matching Bronze table.

THE KEY LINE — how the metadata columns get filled:
      COPY INTO bronze.raw_x (raw_data, _file_name)
      FROM (SELECT $1, METADATA$FILENAME FROM @stage/<subdir>/)
  • $1                -> the whole JSON record -> raw_data (VARIANT)
  • METADATA$FILENAME -> Snowflake's built-in "which file did this row come
                         from" -> _file_name   (this is what we discussed!)
  • source, _loaded_at -> NOT in the column list, so they take their DDL
                          DEFAULTs ('<source>' and CURRENT_TIMESTAMP()).

IDEMPOTENCY: Snowflake tracks load history per file. COPY INTO skips files it
has already loaded, so re-running is safe and won't duplicate rows. (Use FORCE
only to deliberately reload.)

Connects as the LOADER role (Bronze write only). Run directly:
    python -m extractors.loader
"""

from __future__ import annotations

import snowflake.connector

from extractors import config
from extractors.utils import get_logger

log = get_logger("loader")

# Map each ADLS subfolder -> its Bronze target table. One COPY INTO per pair.
SUBDIR_TO_TABLE: dict[str, str] = {
    "stock-prices": "raw_stock_prices",
    "stock-fundamentals": "raw_stock_fundamentals",
    "fred-series": "raw_fred_series",
    "crypto-prices": "raw_crypto_prices",
    "fear-greed": "raw_fear_greed",
}

STAGE = "MACROMARKET.BRONZE.adls_raw_stage"
FILE_FORMAT = "MACROMARKET.BRONZE.json_format"


def _copy_sql(subdir: str, table: str) -> str:
    """Build the COPY INTO statement for one source."""
    return f"""
        COPY INTO MACROMARKET.BRONZE.{table} (raw_data, _file_name)
        FROM (
            SELECT $1, METADATA$FILENAME
            FROM @{STAGE}/{subdir}/
        )
        FILE_FORMAT = (FORMAT_NAME = {FILE_FORMAT})
        ON_ERROR = 'ABORT_STATEMENT'
    """


def load_all() -> None:
    """Run COPY INTO for every source subfolder, logging rows loaded."""
    conn = snowflake.connector.connect(**config.get_snowflake_config())
    try:
        cur = conn.cursor()
        total = 0
        for subdir, table in SUBDIR_TO_TABLE.items():
            cur.execute(_copy_sql(subdir, table))
            rows = cur.fetchall()
            # COPY INTO returns one wide row per file loaded (rows_loaded at index
            # 3). When nothing new is loaded it returns a single short status row
            # instead — so only count rows that actually have the per-file shape.
            file_rows = [r for r in rows if len(r) > 3]
            loaded = sum(r[3] for r in file_rows)
            total += loaded
            log.info("copied", table=table, files=len(file_rows), rows_loaded=loaded)
        log.info("load_complete", total_rows=total)
        cur.close()
    finally:
        conn.close()


if __name__ == "__main__":
    load_all()

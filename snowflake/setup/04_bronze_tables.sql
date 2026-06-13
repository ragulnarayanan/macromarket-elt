-- ===========================================================================
-- 04_bronze_tables.sql
--
-- WHAT: Creates the 6 raw "landing" tables in the BRONZE schema.
-- WHY:  Bronze = raw data exactly as it arrived, never edited. We dump each
--       source's JSON into a single VARIANT column and add metadata columns.
--
-- KEY CONCEPT — the VARIANT column:
--   VARIANT is Snowflake's native "any semi-structured value" type. It stores a
--   whole JSON object/array in one column. We DON'T parse it here — that's the
--   whole point of ELT (Extract-Load-Transform): load raw first, transform later
--   with dbt. Later you query into it with path syntax, e.g.
--       raw_data:close::FLOAT          (extract "close", cast to FLOAT)
--       raw_data:ticker::STRING
--
-- METADATA COLUMNS (added to every Bronze table — your audit trail):
--   source       which extractor produced the row (default per table)
--   _loaded_at   when COPY INTO loaded it (defaults to load time)
--   _file_name   which ADLS file it came from (for tracing/debugging)
--
-- These let dbt deduplicate ("keep the latest _loaded_at per key") and let you
-- trace any row back to its origin file.
--
-- RUN AS: SYSADMIN (owns the tables; LOADER got INSERT/SELECT via FUTURE grants
--         in file 03, which is why 03 must run before 04).
-- ===========================================================================

USE ROLE SYSADMIN;
USE SCHEMA MACROMARKET.BRONZE;

-- Daily OHLCV stock prices from Yahoo Finance.
CREATE TABLE IF NOT EXISTS raw_stock_prices (
    raw_data    VARIANT,
    source      VARCHAR(50)   DEFAULT 'yahoo_finance',
    _loaded_at  TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    _file_name  VARCHAR(500)
);

-- Company fundamentals (market cap, P/E, sector) from Yahoo Finance.
CREATE TABLE IF NOT EXISTS raw_stock_fundamentals (
    raw_data    VARIANT,
    source      VARCHAR(50)   DEFAULT 'yahoo_finance',
    _loaded_at  TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    _file_name  VARCHAR(500)
);

-- Macroeconomic series (rates, CPI, GDP, VIX...) from FRED.
CREATE TABLE IF NOT EXISTS raw_fred_series (
    raw_data    VARIANT,
    source      VARCHAR(50)   DEFAULT 'fred',
    _loaded_at  TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    _file_name  VARCHAR(500)
);

-- Cryptocurrency prices/market cap from CoinGecko.
CREATE TABLE IF NOT EXISTS raw_crypto_prices (
    raw_data    VARIANT,
    source      VARCHAR(50)   DEFAULT 'coingecko',
    _loaded_at  TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    _file_name  VARCHAR(500)
);

-- CNN Fear & Greed index from alternative.me.
CREATE TABLE IF NOT EXISTS raw_fear_greed (
    raw_data    VARIANT,
    source      VARCHAR(50)   DEFAULT 'alternative_me',
    _loaded_at  TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    _file_name  VARCHAR(500)
);

-- News headlines (later fed to Databricks FinBERT) from Yahoo Finance.
CREATE TABLE IF NOT EXISTS raw_news_headlines (
    raw_data    VARIANT,
    source      VARCHAR(50)   DEFAULT 'yahoo_finance_news',
    _loaded_at  TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    _file_name  VARCHAR(500)
);

SHOW TABLES IN SCHEMA MACROMARKET.BRONZE;

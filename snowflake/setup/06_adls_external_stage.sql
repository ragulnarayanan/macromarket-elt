-- ===========================================================================
-- 06_adls_external_stage.sql
--
-- WHAT: Creates a JSON file format and an EXTERNAL STAGE pointing at the ADLS
--       Gen2 container, so Snowflake can read raw files straight out of Azure.
-- WHY:  This is the BRIDGE between Azure storage and Snowflake. An "external
--       stage" is a saved, named pointer to a cloud storage location plus the
--       credentials to read it. Once it exists, the loader simply runs:
--           COPY INTO bronze.raw_stock_prices
--           FROM @adls_raw_stage/stock-prices/2026-06-13.json;
--       and Snowflake pulls the file from ADLS itself — no data flows through
--       your laptop.
--
-- KEY CONCEPTS:
--   FILE FORMAT          reusable parsing rules. STRIP_OUTER_ARRAY = TRUE means
--                        a top-level JSON array [ {...}, {...} ] becomes one ROW
--                        per element instead of one giant row. That's why each
--                        record lands as its own Bronze row.
--   AZURE_SAS_TOKEN      a Shared Access Signature: a scoped, expiring credential
--                        that grants read+list on the container WITHOUT exposing
--                        your account key. You generate it with the `az storage
--                        container generate-sas` command (see azure/setup.sh).
--
-- BEFORE RUNNING: paste your real SAS token where indicated below. The SAS
--                 string starts with "sv=" — paste everything from "sv=" onward,
--                 with NO leading "?".
--
-- RUN AS: SYSADMIN (owns the BRONZE schema where the stage lives).
-- ===========================================================================

USE ROLE SYSADMIN;
USE SCHEMA MACROMARKET.BRONZE;

-- Parsing rules for all our JSON files.
CREATE FILE FORMAT IF NOT EXISTS MACROMARKET.BRONZE.json_format
  TYPE = 'JSON'
  STRIP_OUTER_ARRAY = TRUE   -- explode a top-level array into one row per element
  COMPRESSION = 'AUTO';

-- The pointer to your ADLS Gen2 container "raw-data".
-- NOTE: the URL uses azure://<account>.blob.core.windows.net/<container>.
CREATE STAGE IF NOT EXISTS MACROMARKET.BRONZE.adls_raw_stage
  URL = 'azure://macromarketelt.blob.core.windows.net/raw-data'
  CREDENTIALS = (AZURE_SAS_TOKEN = '<PASTE_YOUR_SAS_TOKEN_HERE>')  -- starts with sv=...
  FILE_FORMAT = MACROMARKET.BRONZE.json_format;

-- The LOADER role runs COPY INTO, so it needs to USE the stage + file format.
GRANT USAGE ON STAGE       MACROMARKET.BRONZE.adls_raw_stage TO ROLE LOADER;
GRANT USAGE ON FILE FORMAT MACROMARKET.BRONZE.json_format    TO ROLE LOADER;

-- Verify Snowflake can actually see your ADLS files (proves the SAS token works).
-- Returns the file list if the credentials + URL are correct.
LIST @MACROMARKET.BRONZE.adls_raw_stage;

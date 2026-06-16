-- ===========================================================================
-- 06_adls_external_stage.sql
--
-- WHAT: Creates a JSON file format and an EXTERNAL STAGE pointing at the ADLS
--       Gen2 container, authenticated with a SAS token.
-- WHY:  An "external stage" is a named pointer to a cloud storage location plus
--       the credentials to read it. Once it exists, the loader runs:
--           COPY INTO bronze.raw_stock_prices
--           FROM @adls_raw_stage/stock-prices/2026-06-13.json;
--       and Snowflake pulls the file straight from ADLS — no data flows through
--       your laptop.
--
-- WHY SAS (and not a storage integration)?
--   A storage integration requires consenting a Snowflake app into your Azure
--   AD directory — which a locked-down student/university tenant won't allow
--   without IT admin approval. A SAS (Shared Access Signature) token is
--   generated from your storage account's OWN access keys and needs NO directory
--   permissions or admin consent. It's the pragmatic choice here.
--
-- KEY CONCEPTS:
--   SAS TOKEN    a scoped, EXPIRING credential string (starts with "sv=") that
--                grants specific permissions (we use read + list) on the
--                container — without exposing your account key.
--   FILE FORMAT  reusable parsing rules. STRIP_OUTER_ARRAY = TRUE turns a
--                top-level JSON array [ {...}, {...} ] into one ROW per element.
--
-- ⚠️ SECURITY — THE REPO IS PUBLIC:
--   DO NOT paste your real SAS token into THIS file and commit it. Instead,
--   either (a) paste the token directly into the Snowflake worksheet when you
--   run this, leaving this committed file with its placeholder; or (b) copy
--   this to "06_adls_external_stage.local.sql" (gitignored) and edit that.
--   The token string starts at "sv=" — paste everything from "sv=" onward,
--   with NO leading "?".
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
-- If you named your storage account something other than "macromarket",
-- update the host below to match.
CREATE STAGE IF NOT EXISTS MACROMARKET.BRONZE.adls_raw_stage
  URL = 'azure://macromarket.blob.core.windows.net/raw-data'
  CREDENTIALS = (AZURE_SAS_TOKEN = '<PASTE_YOUR_SAS_TOKEN_HERE>')  -- starts with sv=...
  FILE_FORMAT = MACROMARKET.BRONZE.json_format;

-- The LOADER role runs COPY INTO, so it needs to USE the stage + file format.
GRANT USAGE ON STAGE       MACROMARKET.BRONZE.adls_raw_stage TO ROLE LOADER;
GRANT USAGE ON FILE FORMAT MACROMARKET.BRONZE.json_format    TO ROLE LOADER;

-- Verify Snowflake can read your ADLS files (proves the SAS token + URL work).
-- 0 files is fine before any data is uploaded; a credential/URL error fails here.
LIST @MACROMARKET.BRONZE.adls_raw_stage;

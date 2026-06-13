-- ===========================================================================
-- 06_adls_external_stage.sql
--
-- WHAT: Creates a JSON file format and an EXTERNAL STAGE pointing at the ADLS
--       Gen2 container — using a STORAGE INTEGRATION (Azure AD identity), so
--       NO credential is ever stored in this file. Safe to commit to a public repo.
-- WHY:  An "external stage" is a named pointer to a cloud storage location.
--       Once it exists, the loader runs:
--           COPY INTO bronze.raw_stock_prices
--           FROM @adls_raw_stage/stock-prices/2026-06-13.json;
--       and Snowflake pulls the file straight from ADLS — no data flows through
--       your laptop.
--
-- WHY STORAGE INTEGRATION (instead of a SAS token):
--   Snowflake registers itself as an app in YOUR Azure Active Directory. You
--   consent to it once and grant it read access on the storage account. After
--   that, Snowflake authenticates to ADLS as that identity — there is no token
--   or key to paste, leak, or rotate. This is the production best practice and
--   keeps secrets entirely out of source control.
--
-- KEY CONCEPTS:
--   STORAGE INTEGRATION  account-level object holding the Azure AD trust + the
--                        list of allowed storage locations. ACCOUNTADMIN-owned.
--   FILE FORMAT          reusable parsing rules. STRIP_OUTER_ARRAY = TRUE turns
--                        a top-level JSON array [ {...}, {...} ] into one ROW per
--                        element (so each record becomes its own Bronze row).
--
-- BEFORE RUNNING: replace <YOUR_AZURE_TENANT_ID> below. Get it with:
--                     az account show --query tenantId --output tsv
--                 (The tenant ID is an identifier, not a secret — safe to keep.)
-- ===========================================================================

-- ===========================================================================
-- STEP 1 — Create the storage integration (ACCOUNTADMIN only).
-- ===========================================================================
USE ROLE ACCOUNTADMIN;

CREATE STORAGE INTEGRATION IF NOT EXISTS azure_adls_integration
  TYPE = EXTERNAL_STAGE
  STORAGE_PROVIDER = 'AZURE'
  ENABLED = TRUE
  AZURE_TENANT_ID = '<YOUR_AZURE_TENANT_ID>'
  -- Snowflake may ONLY read from locations listed here (least privilege).
  STORAGE_ALLOWED_LOCATIONS = ('azure://macromarketelt.blob.core.windows.net/raw-data');

-- ===========================================================================
-- STEP 2 — Consent + grant in Azure (manual, one time).
--   Run DESCRIBE, then from the output:
--     a) AZURE_CONSENT_URL          -> open in a browser, click Accept. This
--                                      adds Snowflake's app to YOUR Azure AD.
--     b) AZURE_MULTI_TENANT_APP_NAME -> the app's name. In Azure, assign it the
--                                      "Storage Blob Data Reader" role on the
--                                      storage account so it can read files.
--        (The exact az command is in azure/setup.sh, Step 7.)
-- ===========================================================================
DESC STORAGE INTEGRATION azure_adls_integration;

-- Let SYSADMIN (which owns the BRONZE schema + stage) use the integration.
GRANT USAGE ON INTEGRATION azure_adls_integration TO ROLE SYSADMIN;

-- ===========================================================================
-- STEP 3 — Create the file format + stage (SYSADMIN owns the BRONZE schema).
-- ===========================================================================
USE ROLE SYSADMIN;
USE SCHEMA MACROMARKET.BRONZE;

-- Parsing rules for all our JSON files.
CREATE FILE FORMAT IF NOT EXISTS MACROMARKET.BRONZE.json_format
  TYPE = 'JSON'
  STRIP_OUTER_ARRAY = TRUE   -- explode a top-level array into one row per element
  COMPRESSION = 'AUTO';

-- The pointer to your ADLS Gen2 container "raw-data".
-- Note: NO credentials here — auth comes from the storage integration.
CREATE STAGE IF NOT EXISTS MACROMARKET.BRONZE.adls_raw_stage
  STORAGE_INTEGRATION = azure_adls_integration
  URL = 'azure://macromarketelt.blob.core.windows.net/raw-data'
  FILE_FORMAT = MACROMARKET.BRONZE.json_format;

-- The LOADER role runs COPY INTO, so it needs to USE the stage + file format.
GRANT USAGE ON STAGE       MACROMARKET.BRONZE.adls_raw_stage TO ROLE LOADER;
GRANT USAGE ON FILE FORMAT MACROMARKET.BRONZE.json_format    TO ROLE LOADER;

-- ===========================================================================
-- STEP 4 — Verify Snowflake can read your ADLS files (proves the integration
-- + role assignment work). 0 files is fine before any data is uploaded.
-- ===========================================================================
LIST @MACROMARKET.BRONZE.adls_raw_stage;

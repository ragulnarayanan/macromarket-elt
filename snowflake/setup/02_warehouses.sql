-- ===========================================================================
-- 02_warehouses.sql
--
-- WHAT: Creates three X-Small virtual warehouses (compute engines).
-- WHY:  In Snowflake, storage and compute are separate. A "warehouse" is the
--       compute cluster that runs your queries. We create one per role so each
--       workload (loading, transforming, reporting) has isolated, separately
--       billable compute. If dbt is hammering TRANSFORMER_WH, the dashboard on
--       REPORTER_WH stays fast.
--
-- COST CONTROLS (critical on a trial):
--   AUTO_SUSPEND = 60     -> spin DOWN after 60s idle (you only pay while running)
--   AUTO_RESUME  = TRUE   -> spin UP automatically when a query arrives
--   INITIALLY_SUSPENDED   -> don't start billing the moment it's created
--   X-SMALL               -> the cheapest size (1 credit/hour, billed per-second)
--
-- RUN AS: SYSADMIN.
-- ===========================================================================

USE ROLE SYSADMIN;

-- Compute for the COPY INTO Bronze load (used by the LOADER role).
CREATE WAREHOUSE IF NOT EXISTS LOADER_WH
  WITH WAREHOUSE_SIZE = 'X-SMALL'
       AUTO_SUSPEND = 60
       AUTO_RESUME = TRUE
       INITIALLY_SUSPENDED = TRUE;

-- Compute for dbt transformations (used by the TRANSFORMER role).
CREATE WAREHOUSE IF NOT EXISTS TRANSFORMER_WH
  WITH WAREHOUSE_SIZE = 'X-SMALL'
       AUTO_SUSPEND = 60
       AUTO_RESUME = TRUE
       INITIALLY_SUSPENDED = TRUE;

-- Compute for the MCP server + Streamlit dashboard (used by the REPORTER role).
CREATE WAREHOUSE IF NOT EXISTS REPORTER_WH
  WITH WAREHOUSE_SIZE = 'X-SMALL'
       AUTO_SUSPEND = 60
       AUTO_RESUME = TRUE
       INITIALLY_SUSPENDED = TRUE;

SHOW WAREHOUSES;

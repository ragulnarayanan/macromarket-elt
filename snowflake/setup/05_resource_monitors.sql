-- ===========================================================================
-- 05_resource_monitors.sql
--
-- WHAT: Creates a resource monitor that caps credit usage and attaches it to
--       all three warehouses.
-- WHY:  Insurance against runaway spend. A resource monitor watches credit
--       consumption over a time window and fires actions at usage thresholds.
--       On a 30-day trial with $400 of credits, an accidental infinite loop or
--       a forgotten warehouse could burn them fast. This is the safety net.
--
-- WHAT THE TRIGGERS DO:
--   at 75%  -> NOTIFY  (email warning, keep running)
--   at 90%  -> NOTIFY  (louder warning, keep running)
--   at 100% -> SUSPEND (stop the warehouses so spend cannot exceed the quota)
--
--   CREDIT_QUOTA = 10  -> 10 credits per MONTHLY window (plenty for this project;
--                         X-Small = 1 credit/hour, so this is ~10 warehouse-hours).
--
-- RUN AS: ACCOUNTADMIN. Resource monitors are account-level objects and ONLY
--         ACCOUNTADMIN can create them or attach them to warehouses.
-- ===========================================================================

USE ROLE ACCOUNTADMIN;

CREATE RESOURCE MONITOR IF NOT EXISTS MACROMARKET_MONITOR
  WITH CREDIT_QUOTA = 10
       FREQUENCY = MONTHLY
       START_TIMESTAMP = IMMEDIATELY
       TRIGGERS ON 75  PERCENT DO NOTIFY
                ON 90  PERCENT DO NOTIFY
                ON 100 PERCENT DO SUSPEND;

-- Attach the monitor to each warehouse so all compute counts against the quota.
ALTER WAREHOUSE LOADER_WH      SET RESOURCE_MONITOR = MACROMARKET_MONITOR;
ALTER WAREHOUSE TRANSFORMER_WH SET RESOURCE_MONITOR = MACROMARKET_MONITOR;
ALTER WAREHOUSE REPORTER_WH    SET RESOURCE_MONITOR = MACROMARKET_MONITOR;

SHOW RESOURCE MONITORS;

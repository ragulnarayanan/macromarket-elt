-- ===========================================================================
-- 01_database_and_schemas.sql
--
-- WHAT: Creates the MACROMARKET database and the three medallion schemas.
-- WHY:  A "schema" in Snowflake is a namespace/folder inside a database.
--       We use one schema per medallion layer so data quality tiers are
--       physically separated and we can grant access per layer (see file 03).
--
-- RUN AS: SYSADMIN (the standard role for creating databases/schemas).
-- ORDER:  Run this FIRST. Everything else lives inside this database.
-- ===========================================================================

USE ROLE SYSADMIN;

-- The single database that holds the entire project.
CREATE DATABASE IF NOT EXISTS MACROMARKET;

-- --- The three medallion layers ---
-- BRONZE: raw, untouched JSON exactly as the APIs returned it (append-only).
CREATE SCHEMA IF NOT EXISTS MACROMARKET.BRONZE;

-- SILVER: cleaned, typed, deduplicated data produced by dbt staging/intermediate.
CREATE SCHEMA IF NOT EXISTS MACROMARKET.SILVER;

-- GOLD: business-ready facts & dimensions, consumed by MCP server + dashboard.
CREATE SCHEMA IF NOT EXISTS MACROMARKET.GOLD;

-- Verify what we just made.
SHOW SCHEMAS IN DATABASE MACROMARKET;

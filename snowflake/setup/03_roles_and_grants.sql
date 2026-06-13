-- ===========================================================================
-- 03_roles_and_grants.sql
--
-- WHAT: Creates the 3 RBAC roles and grants each the MINIMUM access it needs.
-- WHY:  Least privilege. Instead of one all-powerful user, each component of
--       the pipeline runs as a role scoped to exactly what it does:
--
--         LOADER       writes BRONZE only          (ADF COPY INTO)
--         TRANSFORMER  reads BRONZE, writes SILVER+GOLD  (dbt + Databricks)
--         REPORTER     reads GOLD only             (MCP server + Streamlit)
--
--       If the REPORTER credential leaks, the attacker can read Gold but can't
--       touch raw data or delete anything. This separation is what interviewers
--       mean by "RBAC."
--
-- KEY CONCEPT — "FUTURE" grants:
--   dbt and Databricks CREATE NEW TABLES every run. A normal grant only covers
--   tables that exist TODAY. "GRANT ... ON FUTURE TABLES" automatically applies
--   the same access to tables created LATER, so you never re-grant by hand.
--
-- RUN AS: SECURITYADMIN to create roles; SYSADMIN owns the objects being granted.
--         (On a fresh trial, ACCOUNTADMIN can do all of this — switch if a GRANT
--          fails with a privilege error.)
-- ===========================================================================

-- --- Create the roles (needs role-creation privilege) ---
USE ROLE SECURITYADMIN;

CREATE ROLE IF NOT EXISTS LOADER;
CREATE ROLE IF NOT EXISTS TRANSFORMER;
CREATE ROLE IF NOT EXISTS REPORTER;

-- Make the roles manageable under SYSADMIN (standard role hierarchy).
GRANT ROLE LOADER      TO ROLE SYSADMIN;
GRANT ROLE TRANSFORMER TO ROLE SYSADMIN;
GRANT ROLE REPORTER    TO ROLE SYSADMIN;

-- Object grants are issued by the object owner (SYSADMIN created the DB/WH).
USE ROLE SYSADMIN;

-- ===========================================================================
-- LOADER — write to BRONZE only.
-- ===========================================================================
GRANT USAGE  ON DATABASE MACROMARKET            TO ROLE LOADER;
GRANT USAGE  ON SCHEMA MACROMARKET.BRONZE        TO ROLE LOADER;
GRANT CREATE TABLE ON SCHEMA MACROMARKET.BRONZE  TO ROLE LOADER;
GRANT INSERT, SELECT ON ALL TABLES    IN SCHEMA MACROMARKET.BRONZE TO ROLE LOADER;
GRANT INSERT, SELECT ON FUTURE TABLES IN SCHEMA MACROMARKET.BRONZE TO ROLE LOADER;
GRANT USAGE  ON WAREHOUSE LOADER_WH              TO ROLE LOADER;

-- ===========================================================================
-- TRANSFORMER — read BRONZE, full control of SILVER + GOLD.
-- ===========================================================================
GRANT USAGE ON DATABASE MACROMARKET TO ROLE TRANSFORMER;

-- read Bronze
GRANT USAGE  ON SCHEMA MACROMARKET.BRONZE        TO ROLE TRANSFORMER;
GRANT SELECT ON ALL TABLES    IN SCHEMA MACROMARKET.BRONZE TO ROLE TRANSFORMER;
GRANT SELECT ON FUTURE TABLES IN SCHEMA MACROMARKET.BRONZE TO ROLE TRANSFORMER;

-- own Silver
GRANT USAGE ON SCHEMA MACROMARKET.SILVER                 TO ROLE TRANSFORMER;
GRANT CREATE TABLE, CREATE VIEW ON SCHEMA MACROMARKET.SILVER TO ROLE TRANSFORMER;
GRANT ALL ON ALL TABLES    IN SCHEMA MACROMARKET.SILVER  TO ROLE TRANSFORMER;
GRANT ALL ON FUTURE TABLES IN SCHEMA MACROMARKET.SILVER  TO ROLE TRANSFORMER;

-- own Gold
GRANT USAGE ON SCHEMA MACROMARKET.GOLD                   TO ROLE TRANSFORMER;
GRANT CREATE TABLE, CREATE VIEW ON SCHEMA MACROMARKET.GOLD TO ROLE TRANSFORMER;
GRANT ALL ON ALL TABLES    IN SCHEMA MACROMARKET.GOLD    TO ROLE TRANSFORMER;
GRANT ALL ON FUTURE TABLES IN SCHEMA MACROMARKET.GOLD    TO ROLE TRANSFORMER;

GRANT USAGE ON WAREHOUSE TRANSFORMER_WH TO ROLE TRANSFORMER;

-- ===========================================================================
-- REPORTER — read GOLD only.
-- ===========================================================================
GRANT USAGE  ON DATABASE MACROMARKET           TO ROLE REPORTER;
GRANT USAGE  ON SCHEMA MACROMARKET.GOLD         TO ROLE REPORTER;
GRANT SELECT ON ALL TABLES    IN SCHEMA MACROMARKET.GOLD TO ROLE REPORTER;
GRANT SELECT ON FUTURE TABLES IN SCHEMA MACROMARKET.GOLD TO ROLE REPORTER;
GRANT USAGE  ON WAREHOUSE REPORTER_WH           TO ROLE REPORTER;

-- ===========================================================================
-- Assign roles to your user so you can test each one.
-- Replace <YOUR_SNOWFLAKE_USER> with your login name, then run these.
-- (USE ROLE SECURITYADMIN to grant roles to users.)
-- ===========================================================================
-- USE ROLE SECURITYADMIN;
-- GRANT ROLE LOADER      TO USER <YOUR_SNOWFLAKE_USER>;
-- GRANT ROLE TRANSFORMER TO USER <YOUR_SNOWFLAKE_USER>;
-- GRANT ROLE REPORTER    TO USER <YOUR_SNOWFLAKE_USER>;

SHOW ROLES;

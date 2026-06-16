# CLAUDE.md — MacroMarket ELT Pipeline

## Project Overview

This is `macromarket-elt` — an end-to-end Azure-native ELT pipeline built by Rana (Ragul Narayanan Magesh) for his Data Engineering portfolio. Read `MACROMARKET_ELT_PROJECT_SPEC.md` for the complete specification before writing any code.

## How to Work With Rana

- **Explain everything before coding.** Rana is learning Azure services (ADLS Gen2, ADF, Key Vault) for the first time. Treat each phase as a teaching session. Explain WHAT you're building, WHY it exists in the architecture, and HOW it connects to other components.
- **Pause after each explanation.** Wait for "go ahead" or questions before writing code.
- **Annotate code heavily.** Comments should explain "why," not just "what."
- **Build in phase order.** Follow the Build Phases in the spec (Section 14). Complete each phase fully before starting the next.
- **Summarize after each phase.** Recap what was built, how to verify, what's next.
- **Keep outputs concise and scannable.** Rana prefers short, direct communication.

## Tech Stack

- **Cloud:** Azure (ADLS Gen2, Data Factory, Key Vault, DevOps)
- **Warehouse:** Snowflake (East US 2)
- **Transformation:** dbt Core (dbt-snowflake adapter)
- **Orchestration:** Azure Data Factory
- **Data Virtualization:** MCP server (FastMCP + Snowflake connector)
- **Dashboard:** Streamlit
- **CI/CD:** Azure DevOps Pipelines
- **Secrets:** Azure Key Vault (production), `.env` (local dev)
- **Languages:** Python, SQL

## Architecture

```
Extractors → ADLS Gen2 → ADF → Snowflake BRONZE → dbt Silver → dbt Gold
                                                                    ↓
                                                              MCP Server + Streamlit
```

Medallion: Bronze (raw VARIANT) → Silver (staged + intermediate) → Gold (facts + dims)

## Key Commands

```bash
# Extractors
cd extractors && python -m extractors.yahoo_finance     # Run single extractor
cd extractors && python -m extractors.loader             # Load to Snowflake

# dbt
cd dbt_project && dbt deps                               # Install packages
cd dbt_project && dbt run --select silver.staging         # Run staging models
cd dbt_project && dbt run --select gold                   # Run gold models
cd dbt_project && dbt test                                # Run all tests
cd dbt_project && dbt build                               # Run + test everything
cd dbt_project && dbt docs generate && dbt docs serve     # Generate docs site

# MCP Server
cd mcp_server && python server.py                         # Start MCP server

# Streamlit
cd streamlit && streamlit run app.py                      # Start dashboard
```

## File Structure

See Section 13 of the spec for complete repo structure. Key directories:
- `extractors/` — Python data extractors + ADLS uploader + Snowflake loader
- `snowflake/setup/` — DDL scripts (run in order: 01 → 06)
- `azure/` — Azure CLI setup + ADF pipeline definitions
- `dbt_project/` — dbt models, macros, tests, seeds
- `mcp_server/` — MCP tools for LLM data access
- `streamlit/` — Dashboard pages

## Build Order

1. Foundation (Azure + Snowflake setup)
2. Extractors + Bronze load
3. dbt Silver (staging + intermediate)
4. dbt Gold (facts + dims + macros + tests)
5. MCP Server
6. Azure Data Factory orchestration
7. Streamlit Dashboard
8. CI/CD + README + polish

## Important Notes

- Snowflake trial = 30 days. Plan work to maximize usage window.
- All Snowflake credentials come from Key Vault in production, `.env` for local dev.
- Snowflake RBAC: LOADER (Bronze write), TRANSFORMER (dbt), REPORTER (MCP + Streamlit).
- MCP server connects as REPORTER role — Gold-only read access.
- dbt incremental model: `fct_daily_market_snapshot` (use `unique_key='snapshot_date'`).
- Use X-Small warehouses with 60s auto-suspend to conserve credits.
- NOTE: Databricks + FinBERT sentiment enrichment were REMOVED from scope (2026-06-16). No Databricks, no sentiment models/tools/pages, no news-headlines extraction.

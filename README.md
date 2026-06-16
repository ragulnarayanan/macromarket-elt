# MacroMarket ELT Pipeline

> An end-to-end **Azure-native ELT pipeline** ingesting stock, macroeconomic, crypto,
> and sentiment data from 5 sources into **Snowflake** using **medallion architecture**
> (Bronze → Silver → Gold), transformed with **dbt**, enriched with financial sentiment
> via **Azure Databricks (PySpark + FinBERT)**, orchestrated by **Azure Data Factory**,
> and exposed to LLMs through an **MCP server**.

> 🚧 **Status:** Under active construction. This README is a skeleton — full
> documentation, architecture diagram, and screenshots land in Phase 9.

---

## Architecture (high level)

```
Extractors → ADLS Gen2 → ADF → Snowflake BRONZE → dbt Silver → dbt Gold ← Databricks (FinBERT)
                                                                    ↓
                                                              MCP Server + Streamlit
```

| Layer | Snowflake schema | Contents |
|-------|------------------|----------|
| Bronze | `MACROMARKET.BRONZE` | Raw JSON (VARIANT), append-only |
| Silver | `MACROMARKET.SILVER` | Typed, deduplicated, validated (dbt) |
| Gold | `MACROMARKET.GOLD` | Business-ready facts & dimensions (dbt + Databricks) |

## Tech stack

Python · Azure (ADLS Gen2, Data Factory, Databricks, Key Vault, DevOps) · Snowflake ·
dbt Core · PySpark · FinBERT · MCP · Streamlit

## Repository layout

| Directory | Purpose |
|-----------|---------|
| `extractors/` | Python data extractors + ADLS uploader + Snowflake loader |
| `snowflake/setup/` | DDL scripts, run in order `01` → `06` |
| `azure/` | Azure CLI provisioning + ADF pipeline definitions |
| `databricks/` | FinBERT sentiment enrichment notebook |
| `dbt_project/` | dbt models, macros, tests, seeds |
| `mcp_server/` | MCP tools for LLM data access |
| `streamlit/` | Dashboard pages |
| `azure-pipelines/` | Azure DevOps CI/CD definitions |

## Build progress

- [x] **Phase 1** — Foundation (Azure + Snowflake setup) ✅
- [x] Phase 2 — Extractors + Bronze load ✅ *(verified end-to-end: extract → ADLS → COPY INTO Bronze)*
- [x] Phase 3 — dbt Silver ✅ *(6 staging models, 3 seeds, 18 passing tests)*
- [ ] Phase 4 — dbt Gold
- [ ] Phase 5 — Databricks sentiment enrichment
- [ ] Phase 6 — MCP server
- [ ] Phase 7 — Azure Data Factory orchestration
- [ ] Phase 8 — Streamlit dashboard
- [ ] Phase 9 — CI/CD + polish

## Quick start (local dev)

```bash
cp .env.example .env          # then fill in real values
make setup                    # install Python deps
make verify                   # check connectivity to ADLS + Snowflake
```

See `MACROMARKET_ELT_PROJECT_SPEC.md` for the complete specification.

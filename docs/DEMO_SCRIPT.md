# Demo Script (for a 3–5 min Loom walkthrough)

A suggested narration + click path to record a short video of the project. Keep it tight;
the goal is to show the *flow* and a few "wow" moments, not every file.

## 0. Setup (before recording)
```bash
source .venv/bin/activate
set -a; source .env; set +a
```
Have open: the GitHub repo, a terminal, Snowsight, and the Streamlit app.

## 1. The pitch (30s)
"MacroMarket is an end-to-end Azure-native ELT pipeline. It pulls stock, macro, and
crypto data from 4 sources into Snowflake, transforms it with dbt through a medallion
architecture, and serves the Gold layer to an LLM via an MCP server and to a Streamlit
dashboard — all under least-privilege Snowflake roles." Show the README architecture diagram.

## 2. Ingestion → Bronze (45s)
```bash
python -m extractors.run_all --upload --load
```
"Extractors pull each source to JSON, land it in ADLS Gen2 as a durable staging area,
then `COPY INTO` loads it into Bronze as raw VARIANT." In Snowsight:
```sql
SELECT raw_data, _file_name, _loaded_at FROM MACROMARKET.BRONZE.raw_crypto_prices LIMIT 5;
```
Point out `_file_name` (from `METADATA$FILENAME`) and the VARIANT column.

## 3. Transform → Silver → Gold (60s)
```bash
cd dbt_project && dbt build --profiles-dir .
```
"dbt turns raw JSON into typed, deduplicated Silver, then business-ready Gold — 25+
models, 60+ tests, an incremental daily snapshot, custom technical-indicator macros, and
a Python/Snowpark correlation model." Show the test summary `PASS=… ERROR=0`.
Optionally `dbt docs generate && dbt docs serve` and show the lineage graph.

## 4. Governance / RBAC (20s)
"Three roles: LOADER writes Bronze, TRANSFORMER owns Silver/Gold, REPORTER reads Gold
only. The dashboard and the LLM connect as REPORTER — they can't touch raw data."

## 5. MCP server (45s)
In Claude Desktop (configured via `mcp_server/claude_desktop_config.example.json`):
- "What's today's market snapshot?"
- "Compare AAPL, NVDA, and Bitcoin over the last month."
- "How do markets behave across Fed rate regimes?"
"The LLM calls typed tools — never raw SQL — over a read-only connection." (See
`docs/mcp_demo.md` for example outputs.)

## 6. Dashboard (30s)
```bash
streamlit run streamlit/app.py
```
Click through: Market Overview (Fear & Greed gauge), Sector Heatmap, Macro Correlations,
Regime Analysis.

## 7. Orchestration + CI/CD (20s)
Show `azure/adf/` pipeline JSON (or the ADF visual designer) and `azure-pipelines/`
(dbt build + ruff on PRs). "ADF runs this daily at 5 PM ET; Azure DevOps validates dbt
and lints Python on every pull request."

## 8. Close (10s)
"Everything's on GitHub, with sample Gold data and screenshots so it stays demonstrable
after the trial credits expire."

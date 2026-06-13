# MacroMarket ELT Pipeline — Complete Project Specification

## IMPORTANT: Instructions for Claude Code

**You are building this project WITH the developer (Rana). At every stage:**

1. **EXPLAIN BEFORE YOU CODE** — Before writing any file, explain in plain English:
   - What this file/module does and WHY it exists in the architecture
   - How it connects to the other components
   - What design decisions you're making and why
   - Any trade-offs or alternatives you considered
2. **TEACH THE CONCEPTS** — If a concept is new (e.g., Snowflake VARIANT columns, dbt incremental models, MCP tool design, ADF linked services, ADLS Gen2 hierarchical namespace, Databricks Spark clusters), explain it like a senior engineer onboarding a teammate. Use analogies. Don't assume knowledge.
3. **STAGE THE WORK** — Build in the order defined in the "Build Phases" section below. Complete each phase fully (code + tests + explanation) before moving to the next.
4. **PAUSE FOR CONFIRMATION** — After explaining what you're about to build in each phase, wait for Rana to say "go ahead" or ask questions before writing code.
5. **ANNOTATE THE CODE** — Add clear, educational comments in the code itself. Not just "what" but "why."
6. **SUMMARIZE AFTER EACH PHASE** — After completing a phase, give a brief recap: what was built, how to verify it works, and what comes next.

---

## 1. Project Overview

**Project Name:** `macromarket-elt`
**GitHub Repo:** `github.com/ragulnarayanan/macromarket-elt`

**One-liner:** An end-to-end Azure-native ELT pipeline that ingests stock market, macroeconomic, cryptocurrency, and sentiment data from 4 sources, stages in ADLS Gen2, loads into Snowflake (on Azure) using medallion architecture (Bronze → Silver → Gold), transforms with dbt, enriches with financial sentiment analysis via Azure Databricks (PySpark + FinBERT), orchestrates with Azure Data Factory, manages secrets via Azure Key Vault, runs CI/CD through Azure DevOps, and exposes the Gold layer via an MCP server for LLM-powered conversational market analytics.

**Why this project matters for a Data Engineering resume:**
- Demonstrates real-world ELT (not ETL) pattern — the industry standard for cloud warehouses
- Medallion architecture — recognized Databricks/Snowflake design pattern
- Multiple heterogeneous data sources with different ingestion methods
- **Full Azure stack** — ADLS Gen2, Azure Data Factory, Databricks, Key Vault, Azure DevOps (5 Azure services)
- Snowflake-native features (VARIANT, RBAC, external stages)
- dbt with advanced features (incremental models, custom macros, Python models, tests, CI/CD)
- **Databricks for NLP enrichment** — PySpark + FinBERT financial sentiment analysis, bridges DS + DE skills
- MCP server as a data virtualization / governed semantic access layer — cutting-edge, almost no one has this
- Cost-conscious design (auto-suspend, X-Small warehouses, resource monitors)

**Tech Stack (for resume):**
> Python, Azure (ADLS Gen2, Data Factory, Databricks, Key Vault, DevOps), Snowflake, dbt Core, PySpark, FinBERT, MCP, Streamlit, Docker

---

## 2. Architecture

### High-Level Flow

```
[Yahoo Finance] ──┐
[FRED API]     ───┤──→ Python Extractors ──→ ADLS Gen2 (raw/)
[CoinGecko]    ───┤                              │
[Fear & Greed] ──┘                              ▼
                                    Azure Data Factory (orchestrates everything)
                                              │
                            ┌─────────────────┼──────────────────┐
                            ▼                 ▼                  ▼
                    Snowflake BRONZE    dbt (Silver→Gold)    Databricks
                    (COPY INTO from     (staging, intermediate,  (PySpark + FinBERT
                     ADLS external       marts, tests)           sentiment enrichment)
                     stage)                   │                       │
                                              ▼                      ▼
                                         Snowflake GOLD ◄────── fct_sentiment_enriched
                                           │         │
                                           ▼         ▼
                                      MCP Server   Streamlit Dashboard
                                      (Claude)     (visualization)

                    Azure Key Vault ← (secrets for ALL connections)
                    Azure DevOps   ← (CI/CD for dbt + extractors on PRs)
```

### Medallion Architecture Mapping

| Medallion Layer | Snowflake Schema | What Lives Here | Who Writes | Who Reads |
|----------------|-----------------|-----------------|-----------|----------|
| **Bronze** | `MACROMARKET.BRONZE` | Raw VARIANT JSON, append-only, `_loaded_at` timestamp, source metadata | `LOADER` role (via ADF + COPY INTO) | `TRANSFORMER` role (dbt) |
| **Silver** | `MACROMARKET.SILVER` | Typed, deduplicated, validated data. Staging models (1:1 source mapping) + Intermediate models (cross-source joins, technicals) | `TRANSFORMER` role (dbt) | `TRANSFORMER` role (dbt), Databricks |
| **Gold** | `MACROMARKET.GOLD` | Business-ready fact and dimension tables. Aggregated, enriched with sentiment, ready for analytics | `TRANSFORMER` role (dbt + Databricks) | `REPORTER` role (MCP server, Streamlit) |

### RBAC Design (Snowflake Roles)

```
SYSADMIN
├── LOADER         → WRITE to BRONZE (used by ADF COPY INTO activity)
├── TRANSFORMER    → READ BRONZE, WRITE SILVER + GOLD (used by dbt + Databricks)
└── REPORTER       → READ GOLD only (used by MCP server + Streamlit)
```

---

## 3. Data Sources

### 3.1 Yahoo Finance (`yfinance` Python library)

- **Data:** Daily OHLCV (Open, High, Low, Close, Volume), market cap, P/E ratio, sector, industry
- **Universe:** S&P 500 constituents (~503 tickers) + major indices (^GSPC, ^DJI, ^IXIC) + sector ETFs (XLF, XLK, XLE, etc.)
- **Ingestion method:** `yfinance` Python library (no API key needed)
- **Frequency:** Daily (after market close, ~5 PM ET)
- **Rate limits:** No official limit, but use 2-second delays between batch requests
- **Raw format:** JSON (one record per ticker per date)
- **Key fields:** `ticker`, `date`, `open`, `high`, `low`, `close`, `adj_close`, `volume`, `market_cap`, `pe_ratio`, `sector`, `industry`

### 3.2 FRED API (Federal Reserve Economic Data)

- **Data:** Macroeconomic indicators
- **API key:** Free, register at https://fred.stlouisfed.org/docs/api/api_key.html
- **Ingestion method:** REST API (`https://api.stlouisfed.org/fred/series/observations`)
- **Frequency:** Varies by indicator (daily, monthly, quarterly) — ingest daily, let dbt handle alignment
- **Rate limits:** 120 requests per minute (generous)
- **Key series to ingest:**

| Series ID | Name | Frequency | Why It Matters |
|-----------|------|-----------|----------------|
| `DFF` | Federal Funds Effective Rate | Daily | The rate that drives all markets |
| `DGS10` | 10-Year Treasury Yield | Daily | Risk-free rate benchmark |
| `DGS2` | 2-Year Treasury Yield | Daily | Yield curve (10Y-2Y = inversion signal) |
| `CPIAUCSL` | Consumer Price Index (CPI) | Monthly | Inflation gauge |
| `GDPC1` | Real GDP | Quarterly | Economic growth |
| `UNRATE` | Unemployment Rate | Monthly | Labor market health |
| `M2SL` | M2 Money Supply | Monthly | Liquidity / money printing |
| `VIXCLS` | CBOE Volatility Index (VIX) | Daily | Fear gauge |
| `DCOILWTICO` | WTI Crude Oil Price | Daily | Energy/inflation signal |
| `DEXUSEU` | USD/EUR Exchange Rate | Daily | Dollar strength |

- **Raw format:** JSON
- **Key fields:** `series_id`, `date`, `value`, `realtime_start`, `realtime_end`

### 3.3 CoinGecko API

- **Data:** Cryptocurrency prices, market cap, 24h volume, circulating supply
- **API key:** Not needed for free tier (Demo API)
- **Ingestion method:** REST API (`https://api.coingecko.com/api/v3/`)
- **Endpoints:** `/coins/markets` (top N by market cap), `/coins/{id}/market_chart` (historical)
- **Universe:** Top 20 coins by market cap (BTC, ETH, BNB, SOL, XRP, ADA, DOGE, etc.)
- **Frequency:** Daily
- **Rate limits:** 10-30 calls/minute on free tier
- **Key fields:** `coin_id`, `symbol`, `date`, `price_usd`, `market_cap`, `total_volume`, `circulating_supply`

### 3.4 Fear & Greed Index

- **Data:** CNN Fear & Greed Index daily reading (0-100 scale)
- **Source:** Alternative.me API (`https://api.alternative.me/fng/`)
- **Ingestion method:** REST API (no key needed)
- **Frequency:** Daily
- **Key fields:** `date`, `value` (0-100), `classification` (Extreme Fear / Fear / Neutral / Greed / Extreme Greed)

### 3.5 Financial News Headlines (for Databricks sentiment enrichment)

- **Data:** Financial news headlines for S&P 500 companies
- **Source:** Yahoo Finance RSS feeds + `yfinance` news endpoint (free, no key)
- **Ingestion method:** `yfinance` `.news` attribute per ticker + RSS parsing
- **Frequency:** Daily
- **Raw format:** JSON
- **Key fields:** `ticker`, `headline`, `publisher`, `published_date`, `url`
- **Purpose:** Fed into Databricks for FinBERT sentiment scoring → enriches Gold layer

---

## 4. Azure Setup

### 4.1 Azure Free Account

Sign up at https://azure.microsoft.com/en-us/free/:
- **$200 free credit** for 30 days
- **5 GB Blob/ADLS Gen2 free** for 12 months (LRS hot tier)
- **Azure Databricks:** 14-day free trial via Databricks (separate from Azure credits)
- **Azure Data Factory:** first 5 pipeline activities/month free, then pay-per-activity (pennies)
- **Azure Key Vault:** 10,000 operations/month free tier
- **Azure DevOps:** free for up to 5 users, 1 parallel pipeline

### 4.2 Azure Resources to Create

```
Resource Group: rg-macromarket-elt (East US 2)
│
├── Storage Account: macromarketelt
│   Type: StorageV2 with Hierarchical Namespace ENABLED (this makes it ADLS Gen2)
│   └── Container (filesystem): raw-data
│       ├── stock-prices/           # JSON from Yahoo Finance
│       ├── stock-fundamentals/     # JSON from Yahoo Finance fundamentals
│       ├── fred-series/            # JSON from FRED
│       ├── crypto-prices/          # JSON from CoinGecko
│       ├── fear-greed/             # JSON from Fear & Greed
│       └── news-headlines/         # JSON from Yahoo Finance news
│
├── Key Vault: kv-macromarket
│   Secrets:
│   ├── snowflake-account
│   ├── snowflake-user
│   ├── snowflake-password
│   ├── fred-api-key
│   └── adls-connection-string
│
├── Data Factory: adf-macromarket
│   Linked Services:
│   ├── ls_adls_gen2 (ADLS Gen2 connection)
│   ├── ls_snowflake (Snowflake connection)
│   ├── ls_keyvault (Key Vault reference)
│   └── ls_databricks (Databricks workspace)
│   Pipelines:
│   ├── pl_daily_elt (main orchestration pipeline)
│   └── pl_backfill (parameterized historical load)
│
├── Databricks Workspace: dbw-macromarket
│   Cluster: macromarket-etl (Single Node, Standard_DS3_v2, auto-terminate 10 min)
│   Notebooks:
│   └── sentiment_enrichment.py (PySpark + FinBERT)
│
└── Azure DevOps Project: macromarket-elt
    Repos: linked to GitHub (or use Azure Repos)
    Pipelines:
    ├── dbt-ci.yml (PR validation)
    └── lint.yml (code quality)
```

### 4.3 Setup via Azure CLI

```bash
# Install Azure CLI: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli
az login

# Create resource group
az group create --name rg-macromarket-elt --location eastus2

# Create ADLS Gen2 storage account (--hns true = hierarchical namespace = ADLS Gen2)
az storage account create \
  --name macromarketelt \
  --resource-group rg-macromarket-elt \
  --location eastus2 \
  --sku Standard_LRS \
  --kind StorageV2 \
  --hns true \
  --access-tier Hot

# Create filesystem (container) in ADLS Gen2
az storage fs create \
  --name raw-data \
  --account-name macromarketelt

# Create Key Vault
az keyvault create \
  --name kv-macromarket \
  --resource-group rg-macromarket-elt \
  --location eastus2

# Store secrets in Key Vault
az keyvault secret set --vault-name kv-macromarket --name snowflake-account --value "your_account"
az keyvault secret set --vault-name kv-macromarket --name snowflake-user --value "your_user"
az keyvault secret set --vault-name kv-macromarket --name snowflake-password --value "your_password"
az keyvault secret set --vault-name kv-macromarket --name fred-api-key --value "your_key"

# Get connection string for ADLS (save for local dev .env)
az storage account show-connection-string \
  --name macromarketelt \
  --resource-group rg-macromarket-elt

# Generate SAS token for Snowflake external stage
az storage container generate-sas \
  --account-name macromarketelt \
  --name raw-data \
  --permissions rl \
  --expiry 2027-12-31 \
  --output tsv

# Create Data Factory
az datafactory create \
  --name adf-macromarket \
  --resource-group rg-macromarket-elt \
  --location eastus2
```

### 4.4 ADLS Gen2 vs Blob Storage — Why Gen2?

ADLS Gen2 = Blob Storage + hierarchical namespace. Same price, same SDK (`azure-storage-file-datalake` or `azure-storage-blob` — both work). The hierarchical namespace gives you real directories (not just prefix-based virtual folders), ACLs at the directory level, and atomic directory operations. It's what enterprise data lakes use and what shows up in JDs as "ADLS Gen2." Enabling it is one checkbox (`--hns true`) during storage account creation.

---

## 5. Snowflake Setup

### 5.1 Trial Account

When signing up at https://signup.snowflake.com/:
- **Edition:** Enterprise (to access all features during trial)
- **Cloud Provider:** Microsoft Azure
- **Region:** East US 2 (same region as ADLS — zero cross-region transfer fees)
- **Trial:** 30 days, $400 in credits, no credit card needed

### 5.2 Database & Schema DDL

```sql
-- === DATABASE ===
CREATE DATABASE IF NOT EXISTS MACROMARKET;

-- === SCHEMAS (Medallion Layers) ===
CREATE SCHEMA IF NOT EXISTS MACROMARKET.BRONZE;
CREATE SCHEMA IF NOT EXISTS MACROMARKET.SILVER;
CREATE SCHEMA IF NOT EXISTS MACROMARKET.GOLD;

-- === WAREHOUSES (workload isolation + cost tracking) ===
CREATE WAREHOUSE IF NOT EXISTS LOADER_WH
  WITH WAREHOUSE_SIZE = 'X-SMALL' AUTO_SUSPEND = 60 AUTO_RESUME = TRUE INITIALLY_SUSPENDED = TRUE;

CREATE WAREHOUSE IF NOT EXISTS TRANSFORMER_WH
  WITH WAREHOUSE_SIZE = 'X-SMALL' AUTO_SUSPEND = 60 AUTO_RESUME = TRUE INITIALLY_SUSPENDED = TRUE;

CREATE WAREHOUSE IF NOT EXISTS REPORTER_WH
  WITH WAREHOUSE_SIZE = 'X-SMALL' AUTO_SUSPEND = 60 AUTO_RESUME = TRUE INITIALLY_SUSPENDED = TRUE;

-- === ROLES (RBAC) ===
CREATE ROLE IF NOT EXISTS LOADER;
CREATE ROLE IF NOT EXISTS TRANSFORMER;
CREATE ROLE IF NOT EXISTS REPORTER;

GRANT ROLE LOADER TO ROLE SYSADMIN;
GRANT ROLE TRANSFORMER TO ROLE SYSADMIN;
GRANT ROLE REPORTER TO ROLE SYSADMIN;

-- LOADER: write to BRONZE only
GRANT USAGE ON DATABASE MACROMARKET TO ROLE LOADER;
GRANT USAGE ON SCHEMA MACROMARKET.BRONZE TO ROLE LOADER;
GRANT CREATE TABLE ON SCHEMA MACROMARKET.BRONZE TO ROLE LOADER;
GRANT INSERT, SELECT ON ALL TABLES IN SCHEMA MACROMARKET.BRONZE TO ROLE LOADER;
GRANT INSERT, SELECT ON FUTURE TABLES IN SCHEMA MACROMARKET.BRONZE TO ROLE LOADER;
GRANT USAGE ON WAREHOUSE LOADER_WH TO ROLE LOADER;

-- TRANSFORMER: read BRONZE, write SILVER + GOLD
GRANT USAGE ON DATABASE MACROMARKET TO ROLE TRANSFORMER;
GRANT USAGE ON SCHEMA MACROMARKET.BRONZE TO ROLE TRANSFORMER;
GRANT SELECT ON ALL TABLES IN SCHEMA MACROMARKET.BRONZE TO ROLE TRANSFORMER;
GRANT SELECT ON FUTURE TABLES IN SCHEMA MACROMARKET.BRONZE TO ROLE TRANSFORMER;
GRANT USAGE ON SCHEMA MACROMARKET.SILVER TO ROLE TRANSFORMER;
GRANT CREATE TABLE, CREATE VIEW ON SCHEMA MACROMARKET.SILVER TO ROLE TRANSFORMER;
GRANT ALL ON ALL TABLES IN SCHEMA MACROMARKET.SILVER TO ROLE TRANSFORMER;
GRANT ALL ON FUTURE TABLES IN SCHEMA MACROMARKET.SILVER TO ROLE TRANSFORMER;
GRANT USAGE ON SCHEMA MACROMARKET.GOLD TO ROLE TRANSFORMER;
GRANT CREATE TABLE, CREATE VIEW ON SCHEMA MACROMARKET.GOLD TO ROLE TRANSFORMER;
GRANT ALL ON ALL TABLES IN SCHEMA MACROMARKET.GOLD TO ROLE TRANSFORMER;
GRANT ALL ON FUTURE TABLES IN SCHEMA MACROMARKET.GOLD TO ROLE TRANSFORMER;
GRANT USAGE ON WAREHOUSE TRANSFORMER_WH TO ROLE TRANSFORMER;

-- REPORTER: read GOLD only
GRANT USAGE ON DATABASE MACROMARKET TO ROLE REPORTER;
GRANT USAGE ON SCHEMA MACROMARKET.GOLD TO ROLE REPORTER;
GRANT SELECT ON ALL TABLES IN SCHEMA MACROMARKET.GOLD TO ROLE REPORTER;
GRANT SELECT ON FUTURE TABLES IN SCHEMA MACROMARKET.GOLD TO ROLE REPORTER;
GRANT USAGE ON WAREHOUSE REPORTER_WH TO ROLE REPORTER;

-- === RESOURCE MONITOR (cost control) ===
CREATE RESOURCE MONITOR IF NOT EXISTS MACROMARKET_MONITOR
  WITH CREDIT_QUOTA = 10 FREQUENCY = MONTHLY START_TIMESTAMP = IMMEDIATELY
  TRIGGERS ON 75 PERCENT DO NOTIFY ON 90 PERCENT DO NOTIFY ON 100 PERCENT DO SUSPEND;

ALTER WAREHOUSE LOADER_WH SET RESOURCE_MONITOR = MACROMARKET_MONITOR;
ALTER WAREHOUSE TRANSFORMER_WH SET RESOURCE_MONITOR = MACROMARKET_MONITOR;
ALTER WAREHOUSE REPORTER_WH SET RESOURCE_MONITOR = MACROMARKET_MONITOR;
```

### 5.3 Bronze Layer Tables

```sql
USE SCHEMA MACROMARKET.BRONZE;

CREATE TABLE IF NOT EXISTS raw_stock_prices (
    raw_data    VARIANT, source VARCHAR(50) DEFAULT 'yahoo_finance',
    _loaded_at  TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(), _file_name VARCHAR(500));

CREATE TABLE IF NOT EXISTS raw_stock_fundamentals (
    raw_data    VARIANT, source VARCHAR(50) DEFAULT 'yahoo_finance',
    _loaded_at  TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(), _file_name VARCHAR(500));

CREATE TABLE IF NOT EXISTS raw_fred_series (
    raw_data    VARIANT, source VARCHAR(50) DEFAULT 'fred',
    _loaded_at  TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(), _file_name VARCHAR(500));

CREATE TABLE IF NOT EXISTS raw_crypto_prices (
    raw_data    VARIANT, source VARCHAR(50) DEFAULT 'coingecko',
    _loaded_at  TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(), _file_name VARCHAR(500));

CREATE TABLE IF NOT EXISTS raw_fear_greed (
    raw_data    VARIANT, source VARCHAR(50) DEFAULT 'alternative_me',
    _loaded_at  TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(), _file_name VARCHAR(500));

CREATE TABLE IF NOT EXISTS raw_news_headlines (
    raw_data    VARIANT, source VARCHAR(50) DEFAULT 'yahoo_finance_news',
    _loaded_at  TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(), _file_name VARCHAR(500));
```

### 5.4 Azure External Stage

```sql
CREATE FILE FORMAT IF NOT EXISTS MACROMARKET.BRONZE.json_format
  TYPE = 'JSON' STRIP_OUTER_ARRAY = TRUE COMPRESSION = 'AUTO';

CREATE STAGE IF NOT EXISTS MACROMARKET.BRONZE.adls_raw_stage
  URL = 'azure://macromarketelt.blob.core.windows.net/raw-data'
  CREDENTIALS = (AZURE_SAS_TOKEN = '<your_sas_token>')
  FILE_FORMAT = MACROMARKET.BRONZE.json_format;

-- Verify
LIST @MACROMARKET.BRONZE.adls_raw_stage;
```

---

## 6. Python Extractors

### 6.1 Design Principles

- **Each source gets its own extractor class** following a common `BaseExtractor` interface
- **Extract to local JSON first → upload to ADLS Gen2 → COPY INTO Snowflake** (three-step production pattern)
- **ADLS Gen2 is the durable staging area** — if Snowflake load fails, retry from ADLS without re-extracting
- **Idempotent:** Date-based file naming (`stock-prices/2026-06-13.json`) prevents duplicates
- **Configurable:** Support both backfill (historical) and incremental (daily) modes
- **Structured logging** with timestamps, source name, record counts, errors
- **Retry with exponential backoff** for API failures; never silently skip data
- **Secrets from Key Vault** in production (ADF passes them); `.env` for local dev

### 6.2 Project Structure

```
extractors/
├── __init__.py
├── base.py                  # BaseExtractor abstract class
├── yahoo_finance.py         # Stock prices + fundamentals extractor
├── yahoo_news.py            # News headlines extractor (for Databricks)
├── fred.py                  # FRED macroeconomic data extractor
├── coingecko.py             # Crypto prices extractor
├── fear_greed.py            # Fear & Greed index extractor
├── adls_uploader.py         # Upload JSON files to ADLS Gen2
├── loader.py                # Snowflake COPY INTO from ADLS external stage
├── config.py                # Configuration (env vars, date ranges)
├── utils.py                 # Retry logic, date helpers, logging setup
└── requirements.txt
```

### 6.3 BaseExtractor Interface

```python
from abc import ABC, abstractmethod
from datetime import date

class BaseExtractor(ABC):
    @abstractmethod
    def extract(self, start_date: date, end_date: date) -> str:
        """Extract data, save as local JSON. Returns file path."""
        pass

    @abstractmethod
    def get_source_name(self) -> str:
        """Return source identifier for metadata."""
        pass
```

### 6.4 ADLS Uploader

```python
# Pseudocode — uploads local JSON to ADLS Gen2 container
from azure.storage.filedatalake import DataLakeServiceClient

def upload_to_adls(local_path: str, adls_path: str):
    """
    Upload a local JSON file to ADLS Gen2.
    adls_path example: 'stock-prices/2026-06-13.json'
    """
    service_client = DataLakeServiceClient.from_connection_string(conn_str)
    file_system_client = service_client.get_file_system_client("raw-data")
    file_client = file_system_client.get_file_client(adls_path)
    with open(local_path, "rb") as f:
        file_client.upload_data(f, overwrite=True)
```

### 6.5 Dependencies

```
# extractors/requirements.txt
yfinance>=0.2.36
requests>=2.31.0
snowflake-connector-python>=3.6.0
azure-storage-file-datalake>=12.14.0   # ADLS Gen2 SDK
azure-identity>=1.15.0                 # For Key Vault auth
azure-keyvault-secrets>=4.8.0          # For Key Vault secret retrieval
python-dotenv>=1.0.0
tenacity>=8.2.0
structlog>=24.1.0
```

---

## 7. dbt Project

### 7.1 Project Configuration

```yaml
# dbt_project.yml
name: 'macromarket'
version: '1.0.0'
config-version: 2
profile: 'macromarket'

model-paths: ["models"]
test-paths: ["tests"]
seed-paths: ["seeds"]
macro-paths: ["macros"]
snapshot-paths: ["snapshots"]

clean-targets: ["target", "dbt_packages"]

models:
  macromarket:
    silver:
      staging:
        +materialized: view
        +schema: silver
      intermediate:
        +materialized: table
        +schema: silver
    gold:
      +materialized: table
      +schema: gold
      fct_daily_market_snapshot:
        +materialized: incremental
```

### 7.2 dbt Profile

```yaml
# ~/.dbt/profiles.yml
macromarket:
  target: dev
  outputs:
    dev:
      type: snowflake
      account: "{{ env_var('SF_ACCOUNT') }}"
      user: "{{ env_var('SF_USER') }}"
      password: "{{ env_var('SF_PASSWORD') }}"
      role: TRANSFORMER
      warehouse: TRANSFORMER_WH
      database: MACROMARKET
      schema: SILVER
      threads: 4
    ci:
      type: snowflake
      account: "{{ env_var('SF_ACCOUNT') }}"
      user: "{{ env_var('SF_USER') }}"
      password: "{{ env_var('SF_PASSWORD') }}"
      role: TRANSFORMER
      warehouse: TRANSFORMER_WH
      database: MACROMARKET_CI
      schema: SILVER
      threads: 4
```

### 7.3 Model Structure

```
models/
├── bronze/
│   └── _sources.yml                              # Source definitions for all Bronze tables
│
├── silver/
│   ├── staging/
│   │   ├── _stg_models.yml                       # Schema tests
│   │   ├── stg_yahoo__daily_prices.sql           # Flatten VARIANT → typed columns
│   │   ├── stg_yahoo__fundamentals.sql
│   │   ├── stg_fred__macro_indicators.sql
│   │   ├── stg_coingecko__crypto_prices.sql
│   │   ├── stg_alternative__fear_greed.sql
│   │   └── stg_yahoo__news_headlines.sql         # Headlines for Databricks
│   │
│   └── intermediate/
│       ├── _int_models.yml
│       ├── int_stock_prices_with_technicals.sql   # MA, RSI, Bollinger via macros
│       ├── int_macro_pivot.sql                     # Pivot FRED long → wide
│       ├── int_crypto_with_dominance.sql           # BTC dominance %
│       ├── int_yield_curve.sql                     # 10Y-2Y spread, inversion flag
│       └── int_asset_daily_returns.sql             # Normalized % returns
│
├── gold/
│   ├── _gold_models.yml
│   ├── dim_tickers.sql
│   ├── dim_macro_indicators.sql
│   ├── dim_sectors.sql
│   ├── fct_daily_market_snapshot.sql              # INCREMENTAL
│   ├── fct_sector_performance.sql
│   ├── fct_macro_asset_correlation.py             # dbt Python model (Snowpark)
│   ├── fct_regime_analysis.sql
│   └── fct_sentiment_enriched.sql                 # Joins Databricks sentiment output
```

### 7.4 Key dbt Model Design Notes

**`stg_yahoo__daily_prices.sql`** — Extracts typed columns from VARIANT JSON using Snowflake `:field::TYPE` syntax. Deduplicates via `QUALIFY ROW_NUMBER() OVER (PARTITION BY ticker, date ORDER BY _loaded_at DESC) = 1`.

**`int_stock_prices_with_technicals.sql`** — Adds 20/50/200-day MAs, 14-day RSI, Bollinger Bands using window functions and custom dbt macros.

**`int_macro_pivot.sql`** — Pivots FRED from long (one row per series per date) to wide (one row per date, columns for each indicator). Uses Snowflake `PIVOT` or conditional aggregation.

**`int_yield_curve.sql`** — Calculates 10Y-2Y spread, flags inversions. Domain-specific enrichment.

**`fct_daily_market_snapshot.sql`** — INCREMENTAL. Joins all assets + macro + sentiment into one row per date. Only processes new dates on incremental runs.

```sql
{{ config(materialized='incremental', unique_key='snapshot_date', incremental_strategy='merge') }}

SELECT ...
FROM {{ ref('int_stock_prices_with_technicals') }} sp
JOIN {{ ref('int_macro_pivot') }} mp ON sp.date = mp.date
JOIN {{ ref('int_crypto_with_dominance') }} cp ON sp.date = cp.date
LEFT JOIN {{ ref('stg_alternative__fear_greed') }} fg ON sp.date = fg.date

{% if is_incremental() %}
  WHERE sp.date > (SELECT MAX(snapshot_date) FROM {{ this }})
{% endif %}
```

**`fct_macro_asset_correlation.py`** — dbt Python model running on Snowpark. Computes rolling 30/60/90-day correlation matrices using pandas.

**`fct_regime_analysis.sql`** — Identifies macro regimes (hiking/cutting/holding, high/low inflation) and calculates average asset returns per regime. The "wow" model in interviews.

**`fct_sentiment_enriched.sql`** — Joins Databricks-produced sentiment scores back into the Gold layer. Reads from a table that Databricks writes to.

### 7.5 dbt Macros

```
macros/
├── technical_indicators/
│   ├── moving_average.sql        # Reusable MA(column, window)
│   ├── rsi.sql                   # 14-day RSI
│   └── bollinger_bands.sql       # 20-day, 2σ
├── utils/
│   ├── generate_date_spine.sql
│   └── safe_divide.sql
└── tests/
    └── test_no_future_dates.sql  # Custom generic test
```

### 7.6 dbt Tests

**Schema tests:** `not_null`, `unique`, `dbt_utils.unique_combination_of_columns`, `dbt_utils.accepted_range`

**Custom singular tests:**
- `assert_no_future_dates_stock_prices.sql`
- `assert_market_cap_within_bounds.sql` (3σ anomaly detection)

**Source freshness:** `warn_after: 24h`, `error_after: 48h` on all Bronze sources

### 7.7 dbt Packages

```yaml
packages:
  - package: dbt-labs/dbt_utils
    version: [">=1.0.0", "<2.0.0"]
  - package: calogica/dbt_expectations
    version: [">=0.10.0", "<1.0.0"]
```

---

## 8. Azure Databricks — Sentiment Enrichment

### 8.1 Purpose

Databricks serves as the ML/NLP enrichment engine. It reads news headlines from the Silver layer (or directly from ADLS), runs FinBERT (a BERT model fine-tuned for financial sentiment), and writes sentiment scores back to a Snowflake Gold table. This bridges Rana's DS/ML background with DE work in a way that's rare and impressive.

### 8.2 Why Databricks and not a dbt Python model for this?

- FinBERT is a HuggingFace transformer model — it needs GPU or significant CPU, not Snowpark's constrained Python environment
- Databricks gives you a proper Spark cluster with library management
- It demonstrates a real enterprise pattern: Databricks for ML workloads, Snowflake for warehousing, dbt for SQL transformations
- It's another Azure service on the resume

### 8.3 Cluster Configuration

- **Cluster type:** Single Node (cheapest for this workload)
- **VM:** Standard_DS3_v2 (4 cores, 14 GB RAM) — enough for FinBERT batch inference
- **Auto-terminate:** 10 minutes of inactivity
- **Libraries to install:** `transformers`, `torch`, `snowflake-connector-python`

### 8.4 Notebook: `sentiment_enrichment.py`

```python
# This notebook runs on Azure Databricks (PySpark)
# Triggered by Azure Data Factory as a pipeline activity

# --- Step 1: Read news headlines from Snowflake Silver layer ---
from pyspark.sql import SparkSession
import snowflake.connector
import pandas as pd

# Snowflake connection (credentials from Key Vault via ADF, passed as notebook params)
sf_options = {
    "sfURL": dbutils.widgets.get("sf_account"),
    "sfUser": dbutils.widgets.get("sf_user"),
    "sfPassword": dbutils.widgets.get("sf_password"),
    "sfDatabase": "MACROMARKET",
    "sfSchema": "SILVER",
    "sfWarehouse": "TRANSFORMER_WH",
    "sfRole": "TRANSFORMER"
}

# Read headlines from Silver
df_headlines = spark.read \
    .format("snowflake") \
    .options(**sf_options) \
    .option("query", """
        SELECT ticker, headline, published_date
        FROM MACROMARKET.SILVER.stg_yahoo__news_headlines
        WHERE published_date >= DATEADD('day', -1, CURRENT_DATE())
    """) \
    .load()

# --- Step 2: Run FinBERT sentiment analysis ---
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import torch.nn.functional as F

# Load FinBERT (financial domain BERT)
tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert")
model = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert")

def score_sentiment(headline: str) -> dict:
    """Score a single headline. Returns {label, score}."""
    inputs = tokenizer(headline, return_tensors="pt", truncation=True, max_length=512)
    with torch.no_grad():
        outputs = model(**inputs)
    probs = F.softmax(outputs.logits, dim=1)
    labels = ["positive", "negative", "neutral"]
    idx = torch.argmax(probs).item()
    return {"sentiment_label": labels[idx], "sentiment_score": probs[0][idx].item()}

# Apply to all headlines (collect to driver for FinBERT — it's not distributed)
headlines_pd = df_headlines.toPandas()
sentiments = headlines_pd["headline"].apply(score_sentiment).apply(pd.Series)
result = pd.concat([headlines_pd, sentiments], axis=1)

# --- Step 3: Write enriched data back to Snowflake Gold ---
result_spark = spark.createDataFrame(result)
result_spark.write \
    .format("snowflake") \
    .options(**sf_options) \
    .option("sfSchema", "GOLD") \
    .option("dbtable", "databricks_sentiment_output") \
    .mode("append") \
    .save()
```

### 8.5 How dbt consumes Databricks output

```sql
-- models/gold/fct_sentiment_enriched.sql
-- This model reads from the table Databricks writes to and joins with market data

WITH sentiment AS (
    SELECT
        ticker,
        published_date AS date,
        sentiment_label,
        sentiment_score,
        headline
    FROM {{ source('gold_external', 'databricks_sentiment_output') }}
),

daily_avg_sentiment AS (
    SELECT
        ticker,
        date,
        AVG(CASE WHEN sentiment_label = 'positive' THEN sentiment_score
                 WHEN sentiment_label = 'negative' THEN -sentiment_score
                 ELSE 0 END) AS avg_sentiment_score,
        COUNT(*) AS headline_count,
        SUM(CASE WHEN sentiment_label = 'positive' THEN 1 ELSE 0 END) AS positive_count,
        SUM(CASE WHEN sentiment_label = 'negative' THEN 1 ELSE 0 END) AS negative_count
    FROM sentiment
    GROUP BY ticker, date
)

SELECT
    das.*,
    sp.close_price,
    sp.daily_return,
    sp.ma_20,
    sp.sector
FROM daily_avg_sentiment das
LEFT JOIN {{ ref('int_stock_prices_with_technicals') }} sp
    ON das.ticker = sp.ticker AND das.date = sp.date
```

---

## 9. Azure Data Factory — Orchestration

### 9.1 Why ADF over Airflow

- Azure-native — no infrastructure to manage, no Docker Compose
- Visual pipeline designer — screenshot-friendly for README
- Native connectors to ADLS Gen2, Snowflake, Databricks, Key Vault
- Trigger-based scheduling (cron, event-based, tumbling window)
- Pay-per-activity-run pricing (pennies for this project)
- Shows up on Azure DE job descriptions frequently

### 9.2 Pipeline Design: `pl_daily_elt`

```
Schedule Trigger: Daily 5:00 PM ET (Weekdays)
│
├── Activity Group: Extract (parallel)
│   ├── Custom Activity: extract_stocks      (runs Python extractor in Azure Batch / local)
│   ├── Custom Activity: extract_fred
│   ├── Custom Activity: extract_crypto
│   ├── Custom Activity: extract_fear_greed
│   └── Custom Activity: extract_news        (headlines for Databricks)
│
├── On Success (all extracts) ──→
│   Activity: upload_to_adls                  (Python: upload JSONs to ADLS Gen2)
│
├── On Success ──→
│   Activity: snowflake_copy_into             (Script Activity: COPY INTO from ADLS stage)
│
├── On Success ──→
│   Activity: dbt_run_staging                 (Web Activity or Azure Batch: `dbt run --select silver.staging`)
│
├── On Success ──→
│   Activity: dbt_run_intermediate            (Web Activity: `dbt run --select silver.intermediate`)
│
├── On Success ──→
│   Activity: dbt_run_gold                    (Web Activity: `dbt run --select gold`)
│
├── On Success ──→
│   Activity: databricks_sentiment            (Databricks Notebook Activity: sentiment_enrichment.py)
│   Parameters passed from Key Vault: sf_account, sf_user, sf_password
│
├── On Success ──→
│   Activity: dbt_run_sentiment_model         (Web Activity: `dbt run --select fct_sentiment_enriched`)
│
├── On Success ──→
│   Activity: dbt_test                        (Web Activity: `dbt test`)
│
└── On Failure (any step) ──→
    Activity: send_notification               (Web Activity: Slack webhook or email)
```

### 9.3 ADF Linked Services

```json
// ls_adls_gen2
{
    "type": "AzureBlobFS",
    "typeProperties": {
        "url": "https://macromarketelt.dfs.core.windows.net",
        "accountKey": {"type": "AzureKeyVaultSecret", "store": {"referenceName": "ls_keyvault"}, "secretName": "adls-account-key"}
    }
}

// ls_snowflake
{
    "type": "Snowflake",
    "typeProperties": {
        "connectionString": {"type": "AzureKeyVaultSecret", "store": {"referenceName": "ls_keyvault"}, "secretName": "snowflake-connection-string"}
    }
}

// ls_databricks
{
    "type": "AzureDatabricks",
    "typeProperties": {
        "domain": "https://adb-xxxxxxx.azuredatabricks.net",
        "existingClusterId": "your-cluster-id",
        "accessToken": {"type": "AzureKeyVaultSecret", "store": {"referenceName": "ls_keyvault"}, "secretName": "databricks-token"}
    }
}
```

### 9.4 How ADF runs dbt

Since dbt is a CLI tool, ADF can trigger it in several ways:
1. **Azure Batch** — Run dbt commands in a Docker container on Azure Batch (cleanest production pattern)
2. **Web Activity** — Call a lightweight API wrapper (FastAPI) that runs dbt commands (simpler)
3. **Custom Activity** — Run dbt in an Azure Batch pool

For this project, use a **Web Activity** calling a simple FastAPI dbt wrapper deployed as an Azure Container Instance. This is lightweight and demonstrates containerization.

### 9.5 Pipeline Parameters

```json
{
    "pipeline_date": "2026-06-13",  // Overridable for backfill
    "run_mode": "incremental"       // "incremental" or "backfill"
}
```

The backfill pipeline (`pl_backfill`) is identical but accepts a date range and passes it to extractors.

---

## 10. MCP Server (Data Virtualization Layer)

### 10.1 Purpose

The MCP server sits on the Gold layer and exposes curated, read-only tools for LLM consumption. It's a **governed semantic access layer** — the LLM never writes SQL or sees raw data. The MCP server connects as the `REPORTER` role (Gold-only access).

### 10.2 Structure

```
mcp_server/
├── server.py                 # FastMCP entry point
├── tools/
│   ├── __init__.py
│   ├── market_snapshot.py    # get_market_snapshot
│   ├── sector_performance.py # get_sector_performance
│   ├── macro_impact.py       # get_macro_impact
│   ├── asset_comparison.py   # compare_assets
│   ├── regime_analysis.py    # get_regime_analysis
│   └── sentiment_lookup.py   # get_sentiment (NEW — reads Databricks output)
├── db/
│   ├── __init__.py
│   └── snowflake_client.py   # Connection pool, parameterized queries
├── config.py
└── requirements.txt
```

### 10.3 MCP Tools

```python
@mcp.tool()
def get_market_snapshot(date: str = "latest") -> dict:
    """Full market snapshot: indices, crypto, fear/greed, macro, top movers."""

@mcp.tool()
def get_sector_performance(sector: str, period: str = "1M") -> dict:
    """Sector returns with macro context overlay."""

@mcp.tool()
def get_macro_impact(indicator: str, asset: str, lookback_months: int = 12) -> dict:
    """Correlation between a macro indicator and an asset."""

@mcp.tool()
def compare_assets(assets: list[str], metric: str = "returns", period: str = "3M") -> dict:
    """Side-by-side asset comparison."""

@mcp.tool()
def get_regime_analysis(indicator: str = "fed_funds_rate") -> dict:
    """Macro regime identification + avg returns per regime."""

@mcp.tool()
def get_sentiment(ticker: str, days: int = 7) -> dict:
    """Recent news sentiment for a ticker (from Databricks FinBERT analysis)."""
```

### 10.4 Demo with Claude Desktop

Configure `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "macromarket": {
      "command": "python",
      "args": ["path/to/mcp_server/server.py"],
      "env": {
        "SF_ACCOUNT": "...", "SF_USER": "...", "SF_PASSWORD": "..."
      }
    }
  }
}
```

Example queries to demo:
- "What's today's market snapshot?"
- "Compare AAPL, NVDA, and BTC over 3 months"
- "What's the news sentiment on Tesla this week?"
- "During Fed hiking cycles, how does the S&P perform?"

**Screenshot these for the README.**

---

## 11. CI/CD — Azure DevOps Pipelines

### 11.1 dbt CI on Pull Requests

```yaml
# azure-pipelines/dbt-ci.yml
trigger: none
pr:
  branches:
    include: [main]
  paths:
    include: ['dbt_project/**']

pool:
  vmImage: 'ubuntu-latest'

steps:
  - task: UsePythonVersion@0
    inputs:
      versionSpec: '3.11'

  - script: pip install dbt-snowflake
    displayName: 'Install dbt'

  - script: |
      cd dbt_project
      dbt deps
      dbt build --select state:modified+ --target ci --defer --state ./target
    displayName: 'dbt CI build'
    env:
      SF_ACCOUNT: $(SF_ACCOUNT)
      SF_USER: $(SF_USER)
      SF_PASSWORD: $(SF_PASSWORD)
```

### 11.2 Python Linting

```yaml
# azure-pipelines/lint.yml
trigger:
  branches:
    include: [main]

pool:
  vmImage: 'ubuntu-latest'

steps:
  - task: UsePythonVersion@0
  - script: pip install ruff
  - script: ruff check extractors/ mcp_server/
    displayName: 'Lint Python'
```

---

## 12. Streamlit Dashboard

### 12.1 Pages

1. **Market Overview** — Daily snapshot: indices, crypto, fear/greed gauge, macro indicators
2. **Sector Heatmap** — Sector performance vs S&P 500, color-coded
3. **Macro Correlations** — Interactive correlation matrix
4. **Regime Analysis** — Regime timeline with overlaid performance
5. **Sentiment Tracker** — Per-ticker sentiment trend from Databricks output (NEW)

### 12.2 Connection

```python
# Connects as REPORTER role, reads GOLD schema only
# Use st.connection('snowflake') with Streamlit native connector
```

---

## 13. Repository Structure (Final)

```
macromarket-elt/
├── extractors/
│   ├── __init__.py
│   ├── base.py
│   ├── yahoo_finance.py
│   ├── yahoo_news.py
│   ├── fred.py
│   ├── coingecko.py
│   ├── fear_greed.py
│   ├── adls_uploader.py
│   ├── loader.py
│   ├── config.py
│   ├── utils.py
│   └── requirements.txt
│
├── snowflake/
│   ├── setup/
│   │   ├── 01_database_and_schemas.sql
│   │   ├── 02_warehouses.sql
│   │   ├── 03_roles_and_grants.sql
│   │   ├── 04_bronze_tables.sql
│   │   ├── 05_resource_monitors.sql
│   │   └── 06_adls_external_stage.sql
│   └── migrations/
│
├── azure/
│   ├── setup.sh                      # Azure CLI: resource group, ADLS, Key Vault, ADF
│   ├── adf/
│   │   ├── pipeline_daily_elt.json   # ADF pipeline definition (ARM template)
│   │   ├── pipeline_backfill.json
│   │   ├── linked_services/
│   │   │   ├── ls_adls_gen2.json
│   │   │   ├── ls_snowflake.json
│   │   │   ├── ls_keyvault.json
│   │   │   └── ls_databricks.json
│   │   └── triggers/
│   │       └── tr_daily_5pm.json
│   └── README.md
│
├── databricks/
│   ├── notebooks/
│   │   └── sentiment_enrichment.py   # PySpark + FinBERT
│   ├── cluster_config.json
│   └── README.md
│
├── dbt_project/
│   ├── dbt_project.yml
│   ├── packages.yml
│   ├── models/
│   │   ├── bronze/_sources.yml
│   │   ├── silver/
│   │   │   ├── staging/
│   │   │   │   ├── _stg_models.yml
│   │   │   │   ├── stg_yahoo__daily_prices.sql
│   │   │   │   ├── stg_yahoo__fundamentals.sql
│   │   │   │   ├── stg_yahoo__news_headlines.sql
│   │   │   │   ├── stg_fred__macro_indicators.sql
│   │   │   │   ├── stg_coingecko__crypto_prices.sql
│   │   │   │   └── stg_alternative__fear_greed.sql
│   │   │   └── intermediate/
│   │   │       ├── _int_models.yml
│   │   │       ├── int_stock_prices_with_technicals.sql
│   │   │       ├── int_macro_pivot.sql
│   │   │       ├── int_crypto_with_dominance.sql
│   │   │       ├── int_yield_curve.sql
│   │   │       └── int_asset_daily_returns.sql
│   │   └── gold/
│   │       ├── _gold_models.yml
│   │       ├── dim_tickers.sql
│   │       ├── dim_macro_indicators.sql
│   │       ├── dim_sectors.sql
│   │       ├── fct_daily_market_snapshot.sql
│   │       ├── fct_sector_performance.sql
│   │       ├── fct_macro_asset_correlation.py
│   │       ├── fct_regime_analysis.sql
│   │       └── fct_sentiment_enriched.sql
│   ├── macros/
│   │   ├── technical_indicators/
│   │   │   ├── moving_average.sql
│   │   │   ├── rsi.sql
│   │   │   └── bollinger_bands.sql
│   │   └── utils/
│   │       ├── generate_date_spine.sql
│   │       └── safe_divide.sql
│   ├── tests/
│   │   ├── assert_no_future_dates_stock_prices.sql
│   │   └── assert_market_cap_within_bounds.sql
│   └── seeds/
│       ├── sp500_tickers.csv
│       ├── fred_series_metadata.csv
│       └── gics_sectors.csv
│
├── mcp_server/
│   ├── server.py
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── market_snapshot.py
│   │   ├── sector_performance.py
│   │   ├── macro_impact.py
│   │   ├── asset_comparison.py
│   │   ├── regime_analysis.py
│   │   └── sentiment_lookup.py
│   ├── db/
│   │   ├── __init__.py
│   │   └── snowflake_client.py
│   ├── config.py
│   └── requirements.txt
│
├── streamlit/
│   ├── app.py
│   ├── pages/
│   │   ├── 1_market_overview.py
│   │   ├── 2_sector_heatmap.py
│   │   ├── 3_macro_correlations.py
│   │   ├── 4_regime_analysis.py
│   │   └── 5_sentiment_tracker.py
│   └── requirements.txt
│
├── azure-pipelines/
│   ├── dbt-ci.yml
│   └── lint.yml
│
├── .env.example
├── .gitignore
├── Makefile
├── README.md
└── LICENSE
```

---

## 14. Build Phases (Order of Implementation)

### Phase 1: Foundation (Day 1-2)
1. Initialize repo, `.gitignore`, `.env.example`, `README.md` skeleton
2. Set up Azure resources via CLI (resource group, ADLS Gen2, Key Vault, ADF)
3. Create Snowflake trial (Azure, East US 2)
4. Run Snowflake setup SQL (database, schemas, warehouses, roles, grants, Bronze tables, ADLS external stage)
5. Verify connectivity: Python → ADLS Gen2, Python → Snowflake, Snowflake → ADLS stage

### Phase 2: Extractors + Load (Bronze) (Day 3-6)
6. Build `BaseExtractor`, `utils.py`, `config.py`
7. Build Yahoo Finance extractor (start with 10 tickers for dev)
8. Build FRED extractor
9. Build CoinGecko extractor
10. Build Fear & Greed extractor
11. Build Yahoo News extractor
12. Build ADLS uploader (`adls_uploader.py`)
13. Build Snowflake loader (COPY INTO from ADLS external stage)
14. Run full extract → ADLS upload → COPY INTO cycle, verify data in Bronze

### Phase 3: dbt Silver (Day 7-9)
15. Initialize dbt project, define sources (`_sources.yml`)
16. Build staging models (one per source, including news headlines)
17. Add seeds (`sp500_tickers.csv`, `fred_series_metadata.csv`, `gics_sectors.csv`)
18. Write schema tests
19. Run `dbt build` for Silver, verify

### Phase 4: dbt Gold (Day 10-14)
20. Build dimension tables
21. Build intermediate models (technicals, macro pivot, yield curve, returns)
22. Build `fct_daily_market_snapshot` (incremental)
23. Build `fct_sector_performance`
24. Build `fct_regime_analysis`
25. Build `fct_macro_asset_correlation` (Python model)
26. Build dbt macros (technical indicators)
27. Write custom singular tests
28. Run full `dbt build`, verify Gold layer

### Phase 5: Databricks Enrichment (Day 15-17)
29. Set up Databricks workspace + single-node cluster
30. Build `sentiment_enrichment.py` notebook
31. Test: read from Snowflake Silver → run FinBERT → write to Snowflake Gold
32. Build `fct_sentiment_enriched.sql` in dbt (joins sentiment with market data)
33. Run full pipeline: dbt Gold + Databricks + sentiment model

### Phase 6: MCP Server (Day 18-20)
34. Build Snowflake client with connection pooling (REPORTER role)
35. Implement `get_market_snapshot` tool
36. Implement remaining tools including `get_sentiment`
37. Test with Claude Desktop locally
38. Screenshot demo interactions

### Phase 7: Azure Data Factory (Day 21-23)
39. Create ADF linked services (ADLS, Snowflake, Key Vault, Databricks)
40. Build `pl_daily_elt` pipeline (visual designer)
41. Build `pl_backfill` pipeline
42. Set up daily schedule trigger (5 PM ET weekdays)
43. Test end-to-end pipeline run via ADF
44. Screenshot ADF pipeline monitor (success run)

### Phase 8: Streamlit Dashboard (Day 24-25)
45. Build Market Overview page
46. Build remaining pages including Sentiment Tracker
47. Connect via REPORTER role

### Phase 9: CI/CD + Polish (Day 26-28)
48. Set up Azure DevOps project + pipelines
49. Configure dbt CI on PRs
50. Configure linting pipeline
51. Write comprehensive README with architecture diagram (Mermaid)
52. Add `Makefile` for convenience commands
53. Generate + export dbt docs site
54. Record Loom demo video (3-5 min walkthrough)
55. Export sample Gold data as CSVs for `/docs/sample_output/`
56. Screenshot everything: ADF pipeline, Databricks notebook, MCP conversations, Streamlit

---

## 15. README Sections (Write at the End)

1. **Project title + one-liner**
2. **Architecture diagram** (Mermaid)
3. **Tech stack** (badges)
4. **Quick start** (how to run locally)
5. **Data sources** (table with links)
6. **Medallion architecture** (Bronze → Silver → Gold)
7. **Azure services** (ADLS Gen2, ADF, Databricks, Key Vault, DevOps — what each does)
8. **dbt lineage graph** (screenshot from `dbt docs`)
9. **Databricks sentiment enrichment** (screenshot of notebook + example output)
10. **ADF pipeline** (screenshot of visual designer + successful run)
11. **MCP demo** (screenshots of Claude conversations)
12. **Design decisions** — explain WHY:
    - Why ELT over ETL?
    - Why ADLS Gen2 (not plain Blob Storage)?
    - Why ADF over Airflow?
    - Why Databricks for NLP (not dbt Python model)?
    - Why MCP for data virtualization?
    - Why separate Snowflake roles?
    - Why incremental models?
13. **Lessons learned**
14. **Future improvements** (streaming ingestion via Event Hubs, more NLP models, Azure Fabric migration)

---

## 16. Resume Bullet (Final)

> Built **end-to-end Azure ELT pipeline** with **medallion architecture** (Bronze → Silver → Gold) ingesting stock, macro (FRED), crypto, and sentiment data from **5 sources**; staged in **ADLS Gen2**, orchestrated via **Azure Data Factory**, loaded into **Snowflake** via external stages; transformed through **dbt (30+ models, incremental materialization, custom macros)**; enriched with financial sentiment analysis via **Azure Databricks (PySpark + FinBERT)**; secrets managed via **Azure Key Vault**; CI/CD on **Azure DevOps**; exposed Gold layer through **MCP server** for LLM-powered analytics with role-based access controls

---

## 17. Environment Variables

```bash
# .env.example (for local development — in production, all secrets come from Key Vault)

# Snowflake (hosted on Azure)
SF_ACCOUNT=your_account.east-us-2.azure.snowflakecomputing.com
SF_USER=your_user
SF_PASSWORD=your_password
SF_DATABASE=MACROMARKET
SF_WAREHOUSE=LOADER_WH
SF_ROLE=LOADER

# ADLS Gen2
AZURE_STORAGE_ACCOUNT_NAME=macromarketelt
AZURE_STORAGE_ACCOUNT_KEY=your_key
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=...

# FRED API
FRED_API_KEY=your_fred_api_key

# Databricks
DATABRICKS_HOST=https://adb-xxxxxxx.azuredatabricks.net
DATABRICKS_TOKEN=your_token

# MCP Server
MCP_SF_ROLE=REPORTER
MCP_SF_WAREHOUSE=REPORTER_WH
```

---

## 18. Cost Estimates (30-day trial period)

| Service | Estimated Cost | Notes |
|---------|---------------|-------|
| Snowflake | $0 (trial) | $400 credits, X-Small warehouses, auto-suspend |
| ADLS Gen2 | $0 | 5 GB free tier for 12 months |
| Azure Data Factory | $0-2 | First 5 activities/month free |
| Azure Databricks | $0-5 | 14-day trial + pay-per-minute after |
| Azure Key Vault | $0 | 10,000 ops/month free |
| Azure DevOps | $0 | Free for up to 5 users |
| **Total** | **~$0-7** | |

---

## 19. Post-Trial Showcase Strategy

After Snowflake + Databricks trials expire:

1. **dbt docs site** on GitHub Pages — interactive lineage graph, model documentation
2. **Loom video** (3-5 min) — full pipeline walkthrough recorded while live
3. **Screenshots** in README — ADF pipeline, Databricks notebook, MCP conversations, Streamlit
4. **Sample Gold data** exported as CSVs in `/docs/sample_output/`
5. **DuckDB fallback mode** — `dbt-duckdb` adapter for local demo without Snowflake
6. **The code speaks** — Snowflake DDL, dbt models, ADF definitions, Databricks notebook are all in the repo

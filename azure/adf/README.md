# Azure Data Factory — Orchestration

ADF runs the pipeline daily: **extract → ADLS → `COPY INTO` Bronze → dbt Silver → dbt
Gold → dbt test**, on a 5 PM ET weekday schedule.

```
tr_daily_5pm (weekdays 17:00 ET)
   │
   ▼
pl_daily_elt
   extract_and_upload ─► snowflake_copy_into ─► dbt_run_staging ─►
   dbt_run_intermediate ─► dbt_run_gold ─► dbt_test
                                              └─(on Failed)─► notify_failure
```

## Files

| File | Resource |
|------|----------|
| `linked_services/ls_keyvault.json` | Key Vault connection (source of all secrets) |
| `linked_services/ls_adls_gen2.json` | ADLS Gen2 storage (account key from Key Vault) |
| `linked_services/ls_snowflake.json` | Snowflake (LOADER role; password from Key Vault) |
| `pipeline_daily_elt.json` | Main daily pipeline |
| `pipeline_backfill.json` | Date-range historical backfill |
| `triggers/tr_daily_5pm.json` | Weekday 5 PM ET schedule |

## What runs where

- **`snowflake_copy_into`** runs **natively** through the Snowflake linked service —
  no extra compute. The 5 `COPY INTO` statements (one per Bronze table) are embedded
  in the Script activity and use `METADATA$FILENAME` to populate `_file_name`.
- **`extract_*` and `dbt_*`** are **Web Activities** that POST to an **ELT-runner**
  HTTP endpoint, because the Python extractors and dbt CLI need a host to run on.
  This is the only compute you must provide.

### The ELT-runner contract

Stand up a small HTTP service (e.g. FastAPI in an Azure Container Instance, or behind
a Self-Hosted Integration Runtime) that wraps the existing code:

| Endpoint | Body | Runs |
|----------|------|------|
| `POST /extract` | `{"date","mode"}` or `{"start_date","end_date","mode"}` | `python -m extractors.run_all [--start --end] --upload` |
| `POST /dbt` | `{"command":"run","select":"path:models/..."}` / `{"command":"test"}` / `{"command":"build"}` | `dbt <command> [--select ...]` |

Minimal sketch:

```python
# elt_runner.py (FastAPI) — deploy as a container; set SF_* + ADLS env from Key Vault
from fastapi import FastAPI
import subprocess
app = FastAPI()

@app.post("/extract")
def extract(body: dict):
    args = ["python", "-m", "extractors.run_all", "--upload"]
    if body.get("start_date"): args += ["--start", body["start_date"], "--end", body["end_date"]]
    elif body.get("date") not in (None, "auto"): args += ["--start", body["date"], "--end", body["date"]]
    subprocess.run(args, check=True)
    return {"status": "ok"}

@app.post("/dbt")
def dbt(body: dict):
    cmd = ["dbt", body["command"], "--profiles-dir", "."]
    if body.get("select"): cmd += ["--select", body["select"]]
    subprocess.run(cmd, cwd="dbt_project", check=True)
    return {"status": "ok"}
```

Then replace `https://<elt-runner-host>` in the pipeline JSON with its URL. (`COPY INTO`
between extract and dbt needs no runner — it's the native Snowflake step.)

## Deploy

1. **Key Vault secrets** in `kv-macromarket`: `adls-account-key`, `snowflake-password`
   (the SAS/keys the linked services reference).
2. **Grant ADF's managed identity** the *Key Vault Secrets User* role on `kv-macromarket`.
3. **Import the JSON** into ADF Studio — either connect ADF to this Git repo
   (`azure/adf` as the root) so it picks up `linkedService/`, `pipeline/`, `trigger/`
   folders, or recreate each resource and paste the JSON via the "{}" code view.
4. **Fix placeholders**: `<account_identifier>`, `<sf_user>` in `ls_snowflake.json`;
   `<elt-runner-host>` in the pipelines; the webhook URL in `notify_failure`.
5. **Publish**, then **Start** `tr_daily_5pm`.
6. Test with **Trigger Now** on `pl_daily_elt`; screenshot the green run for the README.

## Notes

- The pipeline reflects the post-Databricks scope: **5 sources**, no sentiment activity.
- `notify_failure` currently fires on the final step's failure; for full coverage add
  failure links from each activity or wrap the steps in a parent Try/Catch pipeline.

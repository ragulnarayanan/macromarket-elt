"""
verify_connectivity.py  —  Phase 1, Step 5: prove the foundation works.

WHAT: Runs three independent connectivity checks and prints a ✓/✗ for each:
    1. Python -> ADLS Gen2     (can we authenticate and list the container?)
    2. Python -> Snowflake     (can we log in and run a query?)
    3. Snowflake -> ADLS stage (can Snowflake itself read your Azure files?)

WHY: Before building extractors (Phase 2) we want certainty that every link in
     the chain is wired correctly. Debugging a broken connection is far easier in
     a 90-line script than buried inside a 6-source pipeline.

USAGE:
    cp .env.example .env        # then fill in real values
    pip install -r extractors/requirements.txt
    python -m extractors.verify_connectivity

Each check is independent and wrapped in try/except, so one failure won't hide
the others — you get the full picture in a single run.
"""

import os
import sys

from dotenv import load_dotenv

# Load .env from the project root into environment variables.
load_dotenv()


# --- small helpers for readable pass/fail output ---------------------------
def ok(msg: str) -> None:
    print(f"  \033[32m✓\033[0m {msg}")


def fail(msg: str) -> None:
    print(f"  \033[31m✗\033[0m {msg}")


def check_adls() -> bool:
    """Check 1: authenticate to ADLS Gen2 and list the raw-data container."""
    print("[1/3] Python -> ADLS Gen2")
    try:
        from azure.storage.filedatalake import DataLakeServiceClient

        conn_str = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
        # from_connection_string() is the simplest local-dev auth path.
        service = DataLakeServiceClient.from_connection_string(conn_str)
        fs = service.get_file_system_client("raw-data")
        # Listing paths forces a real authenticated round-trip to Azure.
        paths = list(fs.get_paths())
        ok(f"connected; 'raw-data' container has {len(paths)} path(s)")
        return True
    except KeyError as e:
        fail(f"missing env var {e} — set it in .env")
    except Exception as e:
        fail(f"{type(e).__name__}: {e}")
    return False


def check_snowflake() -> bool:
    """Check 2: log into Snowflake and confirm role/warehouse/version."""
    print("[2/3] Python -> Snowflake")
    try:
        import snowflake.connector

        conn = snowflake.connector.connect(
            account=os.environ["SF_ACCOUNT"],
            user=os.environ["SF_USER"],
            password=os.environ["SF_PASSWORD"],
            role=os.environ.get("SF_ROLE", "LOADER"),
            warehouse=os.environ.get("SF_WAREHOUSE", "LOADER_WH"),
            database=os.environ.get("SF_DATABASE", "MACROMARKET"),
        )
        cur = conn.cursor()
        cur.execute("SELECT CURRENT_VERSION(), CURRENT_ROLE(), CURRENT_WAREHOUSE()")
        version, role, warehouse = cur.fetchone()
        ok(f"connected; Snowflake {version}, role={role}, warehouse={warehouse}")
        cur.close()
        conn.close()
        return True
    except KeyError as e:
        fail(f"missing env var {e} — set it in .env")
    except Exception as e:
        fail(f"{type(e).__name__}: {e}")
    return False


def check_snowflake_stage() -> bool:
    """Check 3: confirm Snowflake can read the ADLS external stage (file 06)."""
    print("[3/3] Snowflake -> ADLS external stage")
    try:
        import snowflake.connector

        conn = snowflake.connector.connect(
            account=os.environ["SF_ACCOUNT"],
            user=os.environ["SF_USER"],
            password=os.environ["SF_PASSWORD"],
            role=os.environ.get("SF_ROLE", "LOADER"),
            warehouse=os.environ.get("SF_WAREHOUSE", "LOADER_WH"),
            database=os.environ.get("SF_DATABASE", "MACROMARKET"),
        )
        cur = conn.cursor()
        # LIST runs server-side: Snowflake reaches into ADLS using the SAS token
        # baked into the stage. Success proves the stage credentials are valid.
        cur.execute("LIST @MACROMARKET.BRONZE.adls_raw_stage")
        rows = cur.fetchall()
        ok(f"stage readable; {len(rows)} file(s) currently in ADLS")
        cur.close()
        conn.close()
        return True
    except Exception as e:
        # Empty stage is fine (0 files); only credential/URL errors fail here.
        fail(f"{type(e).__name__}: {e}")
    return False


def main() -> int:
    print("=" * 60)
    print("MacroMarket — Phase 1 connectivity check")
    print("=" * 60)
    results = [check_adls(), check_snowflake(), check_snowflake_stage()]
    print("-" * 60)
    passed = sum(results)
    print(f"Result: {passed}/3 checks passed.")
    # Exit non-zero if anything failed, so `make verify` / CI can detect it.
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())

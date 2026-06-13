"""
adls_uploader.py — STEP 2 of ingestion: local JSON -> ADLS Gen2.

WHY this step exists: ADLS is the durable landing zone. Once files are here,
the Snowflake load (step 3) can be retried freely without re-hitting any API.
We upload preserving the EXACT relative path (e.g. fear-greed/2026-06-13.json)
so the Snowflake external stage — which points at the container root — finds
each source under its own subfolder.

Auth: connection string from .env (AZURE_STORAGE_CONNECTION_STRING). In
production ADF would use the storage integration / Key Vault instead.

Run directly to upload everything currently under data/:
    python -m extractors.adls_uploader
"""

from __future__ import annotations

from pathlib import Path

from azure.storage.filedatalake import DataLakeServiceClient

from extractors import config
from extractors.utils import get_logger

log = get_logger("adls_uploader")


def _file_system_client():
    """Return a client scoped to the raw-data container."""
    service = DataLakeServiceClient.from_connection_string(
        config.get_adls_connection_string()
    )
    return service.get_file_system_client(config.ADLS_CONTAINER)


def upload_file(local_path: Path, adls_relpath: str) -> None:
    """Upload one local file to ADLS at the given relative path (overwrites)."""
    fs = _file_system_client()
    file_client = fs.get_file_client(adls_relpath)
    with local_path.open("rb") as f:
        # overwrite=True keeps the upload idempotent: re-running a date replaces
        # that day's file rather than erroring or duplicating.
        file_client.upload_data(f, overwrite=True)
    log.info("uploaded", adls_path=adls_relpath, bytes=local_path.stat().st_size)


def upload_all(data_dir: Path | None = None) -> int:
    """Upload every *.json under data/, mirroring its subfolder structure.

    Returns the number of files uploaded.
    """
    data_dir = data_dir or config.OUTPUT_DIR
    files = sorted(data_dir.rglob("*.json"))
    if not files:
        log.warning("no_files_to_upload", data_dir=str(data_dir))
        return 0

    for local_path in files:
        # Relative path under data/ becomes the ADLS path verbatim.
        adls_relpath = local_path.relative_to(data_dir).as_posix()
        upload_file(local_path, adls_relpath)

    log.info("upload_complete", files=len(files))
    return len(files)


if __name__ == "__main__":
    upload_all()

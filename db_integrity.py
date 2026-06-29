"""DuckDB file integrity checks for the HVDC mail app."""

from __future__ import annotations

import hashlib
from pathlib import Path

import duckdb


def sha256_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_duckdb_file(
    path: Path,
    *,
    expected_sha256: str,
    max_bytes: int,
    required_table: str = "emails",
) -> None:
    db_path = Path(path)
    if not db_path.exists():
        raise ValueError(f"DB file does not exist: {db_path}")

    size = db_path.stat().st_size
    if size <= 0:
        raise ValueError("DB file is empty")
    if max_bytes > 0 and size > max_bytes:
        raise ValueError(f"DB file exceeds max size: {size} > {max_bytes}")

    expected = expected_sha256.strip().lower()
    if not expected:
        raise ValueError("EXPECTED_DB_SHA256 is not configured")
    actual = sha256_file(db_path)
    if actual != expected:
        raise ValueError(f"DB checksum mismatch: {actual} != {expected}")

    con = duckdb.connect(str(db_path), read_only=True)
    try:
        found = con.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
            [required_table],
        ).fetchone()[0]
    finally:
        con.close()

    if int(found) != 1:
        raise ValueError(f"Required DuckDB table not found: {required_table}")

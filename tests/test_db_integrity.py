from pathlib import Path

import duckdb
import pytest

from db_integrity import sha256_file, verify_duckdb_file


def _make_db(path: Path, *, create_emails: bool = True) -> None:
    con = duckdb.connect(str(path))
    try:
        if create_emails:
            con.execute('CREATE TABLE emails ("no" INTEGER, subject VARCHAR)')
            con.execute("INSERT INTO emails VALUES (1, 'subject')")
        else:
            con.execute("CREATE TABLE other_table (id INTEGER)")
    finally:
        con.close()


def test_verify_duckdb_file_accepts_matching_hash_schema_and_size(tmp_path):
    db_path = tmp_path / "ok.duckdb"
    _make_db(db_path)

    verify_duckdb_file(
        db_path,
        expected_sha256=sha256_file(db_path),
        max_bytes=db_path.stat().st_size + 1,
    )


def test_verify_duckdb_file_rejects_bad_checksum(tmp_path):
    db_path = tmp_path / "bad_hash.duckdb"
    _make_db(db_path)

    with pytest.raises(ValueError, match="checksum mismatch"):
        verify_duckdb_file(db_path, expected_sha256="0" * 64, max_bytes=db_path.stat().st_size + 1)


def test_verify_duckdb_file_rejects_missing_emails_table(tmp_path):
    db_path = tmp_path / "missing_schema.duckdb"
    _make_db(db_path, create_emails=False)

    with pytest.raises(ValueError, match="Required DuckDB table"):
        verify_duckdb_file(
            db_path,
            expected_sha256=sha256_file(db_path),
            max_bytes=db_path.stat().st_size + 1,
        )


def test_verify_duckdb_file_rejects_oversized_file(tmp_path):
    db_path = tmp_path / "too_large.duckdb"
    _make_db(db_path)

    with pytest.raises(ValueError, match="exceeds max size"):
        verify_duckdb_file(
            db_path,
            expected_sha256=sha256_file(db_path),
            max_bytes=db_path.stat().st_size - 1,
        )

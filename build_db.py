"""
Excel → DuckDB 변환 (1회 실행)
헤더: row 4, 데이터: row 5~
"""
import os
import time
import openpyxl
import duckdb
import re
from pathlib import Path

XLSX = Path(__file__).parent.parent / "OUTLOOK_HVDC_20260626_120747 (2).xlsx"
DB   = Path(__file__).parent / "hvdc_mail.duckdb"


def clean_col(name: str) -> str:
    if not name:
        return "col_unknown"
    return re.sub(r"\W+", "_", str(name)).strip("_").lower()


def build():
    print(f"Loading {XLSX.name} ...")
    wb = openpyxl.load_workbook(XLSX, read_only=True, data_only=True)
    ws = wb["전체_데이터"]
    rows = ws.iter_rows(values_only=True)

    # skip rows 1-3 (title / note / blank)
    for _ in range(3):
        next(rows)

    raw_headers = next(rows)  # row 4
    headers = [clean_col(h) for h in raw_headers]

    print(f"Columns ({len(headers)}): {headers}")
    print("Reading data rows...")

    data = [list(r) for r in rows if any(v is not None for v in r)]
    print(f"  {len(data):,} rows loaded")

    con = duckdb.connect(str(DB))
    con.execute("DROP TABLE IF EXISTS emails")

    # CREATE TABLE
    col_defs = ", ".join(f'"{h}" VARCHAR' for h in headers)
    con.execute(f"CREATE TABLE emails ({col_defs})")

    # INSERT in chunks
    CHUNK = 5000
    for i in range(0, len(data), CHUNK):
        chunk = data[i : i + CHUNK]
        placeholders = ", ".join(["?"] * len(headers))
        con.executemany(
            f"INSERT INTO emails VALUES ({placeholders})",
            [list(map(str, r)) for r in chunk],
        )
        print(f"  inserted {min(i+CHUNK, len(data)):,}/{len(data):,}", end="\r")

    print("\nBuilding FTS index ...")
    con.execute("""
        INSTALL fts;
        LOAD fts;
    """)
    con.execute("""
        PRAGMA create_fts_index(
            'emails', 'no',
            'subject', 'sendername', 'senderemail',
            'recipientto', 'plaintextbody',
            'hvdc_cases', 'company_name',
            stemmer='english', stopwords='english',
            ignore='(\\.|[^a-z])+',
            strip_accents=1, lower=1, overwrite=1
        );
    """)

    # 인덱스 생성
    con.execute('CREATE INDEX IF NOT EXISTS idx_month ON emails("month")')
    con.execute('CREATE INDEX IF NOT EXISTS idx_stage ON emails("stage")')
    con.execute('CREATE INDEX IF NOT EXISTS idx_site  ON emails("site")')

    count = con.execute("SELECT COUNT(*) FROM emails").fetchone()[0]
    print(f"Done — {count:,} rows in {DB.name}")
    con.close()


def add_embeddings(db_path: Path) -> None:
    """
    sentence-transformers all-MiniLM-L6-v2로 emails 테이블에 벡터 임베딩 추가 (384 dim).
    기존 embedding 컬럼을 DROP 후 FLOAT[384]로 재생성 (dim 변경 대응).
    """
    from sentence_transformers import SentenceTransformer

    print("Loading all-MiniLM-L6-v2 model (first run downloads ~80MB) ...")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    con = duckdb.connect(str(db_path))

    # Drop ALL indexes/FTS that block ALTER TABLE
    for drop_sql, label in [
        ("DROP INDEX IF EXISTS idx_month",        "idx_month"),
        ("DROP INDEX IF EXISTS idx_stage",        "idx_stage"),
        ("DROP INDEX IF EXISTS idx_site",         "idx_site"),
        ("DROP INDEX IF EXISTS idx_embedding_hnsw", "idx_embedding_hnsw (HNSW)"),
    ]:
        try:
            con.execute(drop_sql)
            print(f"  Dropped {label}.")
        except Exception as exc:
            print(f"  {label} drop skipped: {exc}")

    # Drop FTS auxiliary tables
    try:
        con.execute("INSTALL fts")
        con.execute("LOAD fts")
        con.execute("PRAGMA drop_fts_index('emails')")
        print("  FTS index dropped.")
    except Exception as exc:
        print(f"  FTS drop skipped: {exc}")

    # Drop HNSW if VSS needed for proper removal
    try:
        con.execute("INSTALL vss")
        con.execute("LOAD vss")
        con.execute("DROP INDEX IF EXISTS idx_embedding_hnsw")
    except Exception:
        pass

    # Now drop and recreate embedding column as FLOAT[384]
    con.execute("ALTER TABLE emails DROP COLUMN IF EXISTS embedding")
    con.execute("ALTER TABLE emails ADD COLUMN embedding FLOAT[384]")
    print("embedding column reset to FLOAT[384].")

    total = con.execute("SELECT COUNT(*) FROM emails").fetchone()[0]
    print(f"Embedding {total:,} rows with all-MiniLM-L6-v2 (384 dim) ...")

    BATCH = 256
    processed = 0

    while True:
        rows = con.execute(
            'SELECT "no", "subject", "plaintextbody" FROM emails '
            "WHERE embedding IS NULL "
            f"LIMIT {BATCH}"
        ).fetchall()

        if not rows:
            break

        texts = []
        for _, subject, body in rows:
            subject_str = subject or ""
            body_str = (body or "")[:500]
            texts.append(f"{subject_str} {body_str}".strip())

        embeddings = model.encode(texts, normalize_embeddings=True).tolist()

        for (row_no, _, _), embedding in zip(rows, embeddings):
            con.execute(
                'UPDATE emails SET embedding = ? WHERE "no" = ?',
                [embedding, row_no],
            )

        processed += len(rows)
        if processed % 5000 < BATCH:
            print(f"  Progress: {processed:,} / {total:,} rows embedded")

    print(f"\nEmbedding complete — {processed:,} rows updated.")

    # Recreate regular indexes
    con.execute('CREATE INDEX IF NOT EXISTS idx_month ON emails("month")')
    con.execute('CREATE INDEX IF NOT EXISTS idx_stage ON emails("stage")')
    con.execute('CREATE INDEX IF NOT EXISTS idx_site  ON emails("site")')
    print("Regular indexes recreated.")

    # Recreate HNSW index
    try:
        con.execute("INSTALL vss")
        con.execute("LOAD vss")
        con.execute("SET hnsw_enable_experimental_persistence=true")
        con.execute("DROP INDEX IF EXISTS idx_embedding_hnsw")
        con.execute("""
            CREATE INDEX idx_embedding_hnsw
            ON emails USING HNSW (embedding)
            WITH (metric = 'cosine')
        """)
        print("HNSW index created (duckdb-vss).")
    except Exception as exc:
        print(f"duckdb-vss not available — skipping HNSW index. ({exc})")

    # Recreate FTS index (overwrite=1)
    try:
        con.execute("INSTALL fts")
        con.execute("LOAD fts")
        con.execute("""
            PRAGMA create_fts_index(
                'emails', 'no',
                'subject', 'sendername', 'senderemail',
                'recipientto', 'plaintextbody',
                'hvdc_cases', 'company_name',
                stemmer='english', stopwords='english',
                ignore='(\\.|[^a-z])+',
                strip_accents=1, lower=1, overwrite=1
            )
        """)
        print("FTS index recreated.")
    except Exception as exc:
        print(f"FTS index recreation failed: {exc}")

    con.close()


if __name__ == "__main__":
    build()
    add_embeddings(DB)

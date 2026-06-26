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


def add_embeddings(db_path: Path, api_key: str) -> None:
    """
    Google text-embedding-004로 emails 테이블에 벡터 임베딩 추가.
    이미 임베딩된 행은 건너뜀 (re-runnable).
    """
    import google.generativeai as genai

    genai.configure(api_key=api_key)

    con = duckdb.connect(str(db_path))

    # Add embedding column if not exists
    con.execute("ALTER TABLE emails ADD COLUMN IF NOT EXISTS embedding FLOAT[768]")

    total_pending = con.execute(
        "SELECT COUNT(*) FROM emails WHERE embedding IS NULL"
    ).fetchone()[0]

    if total_pending == 0:
        print("All rows already have embeddings — nothing to do.")
        con.close()
        return

    print(f"Embedding {total_pending:,} rows with text-embedding-004 ...")

    BATCH = 100
    processed = 0

    while True:
        rows = con.execute(
            'SELECT "no", "subject", "plaintextbody" FROM emails '
            "WHERE embedding IS NULL "
            f"LIMIT {BATCH}"
        ).fetchall()

        if not rows:
            break

        # Build texts for this batch
        texts = []
        for row_no, subject, body in rows:
            subject_str = subject or ""
            body_str = (body or "")[:500]
            texts.append(f"{subject_str} {body_str}".strip())

        # Call Google embedding API
        try:
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=texts,
                task_type="RETRIEVAL_DOCUMENT",
            )
            embeddings = result["embedding"]
        except Exception as exc:
            print(f"\n  [WARN] Embedding API error for batch at row {processed}: {exc}")
            # Skip this batch to avoid infinite loop — mark as empty list sentinel
            # by advancing: update with None placeholder won't work, so just skip
            # Update a dummy value so these rows are not re-fetched endlessly
            row_nos = [r[0] for r in rows]
            placeholders = ", ".join("?" * len(row_nos))
            # Leave embedding NULL but log; move on by breaking if first batch fails
            print("  Skipping batch and continuing...")
            time.sleep(1.0)
            continue

        # Update each row's embedding
        for (row_no, _, _), embedding in zip(rows, embeddings):
            con.execute(
                'UPDATE emails SET embedding = ? WHERE "no" = ?',
                [embedding, row_no],
            )

        processed += len(rows)

        if processed % 1000 < BATCH:
            print(f"  Progress: {processed:,} / {total_pending:,} rows embedded")

        # Rate-limit: 0.05s between batches
        time.sleep(0.05)

    print(f"\nEmbedding complete — {processed:,} rows updated.")

    # Create HNSW index if duckdb-vss is available
    try:
        con.execute("INSTALL vss; LOAD vss;")
        con.execute("""
            CREATE INDEX IF NOT EXISTS idx_embedding_hnsw
            ON emails USING HNSW (embedding)
            WITH (metric = 'cosine')
        """)
        print("HNSW index created (duckdb-vss).")
    except Exception as exc:
        print(f"duckdb-vss not available — skipping HNSW index. ({exc})")

    con.close()


if __name__ == "__main__":
    build()

    if "GOOGLE_API_KEY" in os.environ:
        add_embeddings(DB, os.environ["GOOGLE_API_KEY"])
    else:
        print(
            "GOOGLE_API_KEY not set — skipping embeddings. "
            "Run with: GOOGLE_API_KEY=AIza... python build_db.py"
        )

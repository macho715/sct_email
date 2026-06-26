"""
Excel → DuckDB 변환 (1회 실행)
헤더: row 4, 데이터: row 5~
"""
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


if __name__ == "__main__":
    build()

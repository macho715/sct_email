"""
Search evaluation harness — HVDC Email Search
Metrics: recall@K, MRR@K, zero_result_rate, p95_latency_ms

Usage:
    python eval/run_search_eval.py [--db PATH] [--top-k N] [--mode fts|chunk|email|all]

Modes:
    fts    — BM25 full-text search only
    chunk  — chunk-level HNSW semantic search (primary, email_chunks table)
    email  — email-level HNSW semantic search (emails.embedding fallback)
    all    — run all three and compare (default)
"""
import argparse
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML not installed. Run: pip install pyyaml")
    sys.exit(1)

try:
    import duckdb
except ImportError:
    print("ERROR: duckdb not installed. Run: pip install duckdb")
    sys.exit(1)


QUERIES_FILE = Path(__file__).parent / "queries.yaml"
EMBED_MODEL  = "paraphrase-multilingual-MiniLM-L12-v2"
EMBED_DIM    = 384


# ── helpers ──────────────────────────────────────────────────────────

def _load_queries():
    with open(QUERIES_FILE, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data["queries"]


def _load_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(EMBED_MODEL)


def _encode(model, query: str) -> list:
    vec = model.encode([query], normalize_embeddings=True)[0]
    return vec.tolist()


def _has_table(con, table_name: str) -> bool:
    row = con.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
        [table_name],
    ).fetchone()
    return bool(row and row[0])


def _has_column(con, table_name: str, column_name: str) -> bool:
    row = con.execute(
        "SELECT COUNT(*) FROM information_schema.columns "
        "WHERE table_name = ? AND column_name = ?",
        [table_name, column_name],
    ).fetchone()
    return bool(row and row[0])


def _has_chunk_embeddings(con) -> bool:
    if not _has_table(con, "email_chunks"):
        return False
    row = con.execute(
        "SELECT COUNT(*) FROM email_chunks WHERE embedding IS NOT NULL LIMIT 1"
    ).fetchone()
    return bool(row and row[0] > 0)


def _has_email_embeddings(con) -> bool:
    if not _has_column(con, "emails", "embedding"):
        return False
    row = con.execute(
        "SELECT COUNT(*) FROM emails WHERE embedding IS NOT NULL LIMIT 1"
    ).fetchone()
    return bool(row and row[0] > 0)


# ── search functions ──────────────────────────────────────────────────

def search_fts(con, query: str, top_k: int) -> tuple[list[str], float]:
    """BM25 full-text search. Returns (nos, latency_ms)."""
    t0 = time.perf_counter()
    try:
        rows = con.execute(
            f"""
            SELECT "no"
            FROM emails
            WHERE fts_main_emails.match_bm25("no", ?) IS NOT NULL
            ORDER BY fts_main_emails.match_bm25("no", ?) DESC
            LIMIT {top_k}
            """,
            [query, query],
        ).fetchall()
        nos = [str(r[0]) for r in rows]
    except Exception:
        nos = []
    latency = (time.perf_counter() - t0) * 1000
    return nos, latency


def search_email_embedding(con, qvec: list, top_k: int) -> tuple[list[str], float]:
    """Email-level cosine search on emails.embedding. Returns (nos, latency_ms)."""
    t0 = time.perf_counter()
    try:
        rows = con.execute(
            f"""
            SELECT "no"
            FROM emails
            WHERE embedding IS NOT NULL
            ORDER BY array_cosine_similarity(embedding, ?::FLOAT[{EMBED_DIM}]) DESC
            LIMIT {top_k}
            """,
            [qvec],
        ).fetchall()
        nos = [str(r[0]) for r in rows]
    except Exception:
        nos = []
    latency = (time.perf_counter() - t0) * 1000
    return nos, latency


def search_chunk_embedding(con, qvec: list, top_k: int) -> tuple[list[str], float]:
    """Chunk-level cosine search on email_chunks (HNSW). Returns (nos, latency_ms).

    Fetches top (top_k × 10) chunks, deduplicates by email keeping the best
    chunk score, then returns top_k unique email nos.
    """
    fetch_limit = top_k * 10
    t0 = time.perf_counter()
    try:
        rows = con.execute(
            f"""
            WITH top_chunks AS (
                SELECT "no",
                       array_cosine_similarity(embedding, ?::FLOAT[{EMBED_DIM}]) AS score
                FROM email_chunks
                WHERE embedding IS NOT NULL
                ORDER BY score DESC
                LIMIT {fetch_limit}
            )
            SELECT "no", MAX(score) AS max_score
            FROM top_chunks
            GROUP BY "no"
            ORDER BY max_score DESC
            LIMIT {top_k}
            """,
            [qvec],
        ).fetchall()
        nos = [str(r[0]) for r in rows]
    except Exception:
        nos = []
    latency = (time.perf_counter() - t0) * 1000
    return nos, latency


# ── metric computation ────────────────────────────────────────────────

def recall_at_k(retrieved: list[str], expected: list[str], k: int) -> float | None:
    if not expected:
        return None
    top_k = set(retrieved[:k])
    hits = sum(1 for no in expected if no in top_k)
    return hits / len(expected)


def mrr_at_k(retrieved: list[str], expected: list[str], k: int) -> float | None:
    if not expected:
        return None
    expected_set = set(expected)
    for rank, no in enumerate(retrieved[:k], start=1):
        if no in expected_set:
            return 1.0 / rank
    return 0.0


def p95(values: list[float]) -> float:
    if not values:
        return 0.0
    return float(np.percentile(values, 95))


# ── per-run evaluation ────────────────────────────────────────────────

def evaluate_mode(
    con,
    queries: list[dict],
    mode: str,
    model,
    top_k: int,
) -> dict:
    """
    Run all queries in a given mode.

    Returns a dict:
        {
            "mode": str,
            "rows": [{"id", "category", "query", "nos", "latency_ms",
                       "recall", "mrr", "result_count"}],
            "latencies": [float],
        }
    """
    rows = []
    latencies = []
    qvec_cache: dict[str, list] = {}

    for q in queries:
        qid       = q["id"]
        category  = q["category"]
        query     = q["query"]
        expected  = [str(n) for n in (q.get("expected_nos") or [])]

        # encode once per unique query text
        if mode in ("chunk", "email"):
            if query not in qvec_cache:
                qvec_cache[query] = _encode(model, query)
            qvec = qvec_cache[query]

        # search
        if mode == "fts":
            nos, latency = search_fts(con, query, top_k)
        elif mode == "chunk":
            nos, latency = search_chunk_embedding(con, qvec, top_k)
        elif mode == "email":
            nos, latency = search_email_embedding(con, qvec, top_k)
        else:
            nos, latency = [], 0.0

        latencies.append(latency)

        recall = recall_at_k(nos, expected, top_k)
        mrr    = mrr_at_k(nos, expected, top_k)

        rows.append({
            "id":           qid,
            "category":     category,
            "query":        query,
            "nos":          nos,
            "latency_ms":   latency,
            "recall":       recall,
            "mrr":          mrr,
            "result_count": len(nos),
        })

    return {"mode": mode, "rows": rows, "latencies": latencies}


# ── report generation ─────────────────────────────────────────────────

def _fmt(val, fmt=".3f", none_str="N/A"):
    if val is None:
        return none_str
    return format(val, fmt)


def print_report(run: dict, top_k: int):
    mode    = run["mode"]
    rows    = run["rows"]
    lats    = run["latencies"]

    all_recall  = [r["recall"] for r in rows if r["recall"] is not None]
    all_mrr     = [r["mrr"]    for r in rows if r["mrr"]    is not None]

    zero_rows       = [r for r in rows if r["category"] == "zero_result"]
    zero_correct    = sum(1 for r in zero_rows if r["result_count"] == 0)
    zero_total      = len(zero_rows)
    zero_rate       = zero_correct / zero_total if zero_total else None

    print(f"\n{'='*60}")
    print(f"  Mode: {mode.upper()}")
    print(f"{'='*60}")

    # per-category
    categories = sorted({r["category"] for r in rows})
    print(f"\n{'Category':<15} {'Recall@' + str(top_k):<12} {'MRR@' + str(top_k):<10} {'P95ms':<10} {'#Queries'}")
    print("-" * 60)
    for cat in categories:
        cat_rows = [r for r in rows if r["category"] == cat]
        cat_rec  = [r["recall"] for r in cat_rows if r["recall"] is not None]
        cat_mrr  = [r["mrr"]    for r in cat_rows if r["mrr"]    is not None]
        cat_lats = [r["latency_ms"] for r in cat_rows]

        avg_rec = sum(cat_rec) / len(cat_rec) if cat_rec else None
        avg_mrr = sum(cat_mrr) / len(cat_mrr) if cat_mrr else None

        print(
            f"{cat:<15} "
            f"{_fmt(avg_rec):<12} "
            f"{_fmt(avg_mrr):<10} "
            f"{_fmt(p95(cat_lats), '.1f'):<10} "
            f"{len(cat_rows)}"
        )

    print("-" * 60)
    avg_rec = sum(all_recall) / len(all_recall) if all_recall else None
    avg_mrr = sum(all_mrr)    / len(all_mrr)    if all_mrr    else None
    print(
        f"{'OVERALL':<15} "
        f"{_fmt(avg_rec):<12} "
        f"{_fmt(avg_mrr):<10} "
        f"{_fmt(p95(lats), '.1f'):<10} "
        f"{len(rows)}"
    )

    print(f"\nZero-result rate : {_fmt(zero_rate, '.1%', 'N/A')} "
          f"({zero_correct}/{zero_total})")
    print(f"P95 latency (ms) : {p95(lats):.1f}")
    n_ground = sum(1 for r in rows if r["recall"] is not None)
    if n_ground == 0:
        print(
            f"\nNOTE: Recall/MRR are N/A — no expected_nos defined in queries.yaml.\n"
            f"      Run this script, review the output CSV, fill in expected_nos,\n"
            f"      then re-run for recall/MRR metrics."
        )


def save_csv(runs: list[dict], out_path: Path):
    """Write per-query results to CSV for annotation."""
    import csv

    header = ["id", "category", "query", "mode", "result_count",
              "latency_ms", "recall", "mrr", "top10_nos"]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        for run in runs:
            mode = run["mode"]
            for r in run["rows"]:
                w.writerow({
                    "id":           r["id"],
                    "category":     r["category"],
                    "query":        r["query"],
                    "mode":         mode,
                    "result_count": r["result_count"],
                    "latency_ms":   f"{r['latency_ms']:.1f}",
                    "recall":       _fmt(r["recall"]),
                    "mrr":          _fmt(r["mrr"]),
                    "top10_nos":    "|".join(r["nos"]),
                })
    print(f"\nResults saved to: {out_path}")


# ── main ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="HVDC Email Search Eval")
    parser.add_argument(
        "--db", default=str(ROOT / "hvdc_mail.duckdb"),
        help="Path to DuckDB database (default: hvdc_mail.duckdb)",
    )
    parser.add_argument(
        "--top-k", type=int, default=10,
        help="Recall/MRR cutoff (default: 10)",
    )
    parser.add_argument(
        "--mode", choices=["fts", "chunk", "email", "all"], default="all",
        help="Search mode (default: all)",
    )
    parser.add_argument(
        "--out", default=str(Path(__file__).parent / "eval_results.csv"),
        help="CSV output path",
    )
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"ERROR: Database not found: {db_path}")
        print("Run build_db.py first to create the database.")
        sys.exit(1)

    print(f"Loading queries from {QUERIES_FILE} ...")
    queries = _load_queries()
    print(f"  {len(queries)} queries loaded.")

    print(f"\nConnecting to {db_path.name} ...")
    con = duckdb.connect(str(db_path), read_only=True)

    # Load extensions
    for ext in ("fts", "vss"):
        try:
            con.execute(f"LOAD {ext};")
        except Exception:
            pass

    # Determine available modes
    has_fts   = True
    has_chunk = _has_chunk_embeddings(con)
    has_email = _has_email_embeddings(con)

    print(f"  FTS available:   {has_fts}")
    print(f"  Chunk emb:       {has_chunk}")
    print(f"  Email emb:       {has_email}")

    modes_to_run: list[str] = []
    if args.mode == "all":
        if has_fts:
            modes_to_run.append("fts")
        if has_chunk:
            modes_to_run.append("chunk")
        if has_email and not has_chunk:
            # only add email-level if chunk not available
            modes_to_run.append("email")
    else:
        modes_to_run = [args.mode]

    # Load embedding model if needed
    model = None
    if any(m in modes_to_run for m in ("chunk", "email")):
        print(f"\nLoading embedding model {EMBED_MODEL} ...")
        model = _load_model()
        print("  Model loaded.")

    print(f"\nRunning eval (top_k={args.top_k}, modes={modes_to_run}) ...")
    runs = []
    for mode in modes_to_run:
        print(f"\n  Mode: {mode} ...", flush=True)
        run = evaluate_mode(con, queries, mode, model, args.top_k)
        runs.append(run)

    con.close()

    # Print reports
    print("\n" + "=" * 60)
    print("  HVDC Email Search — Evaluation Report")
    print("=" * 60)
    print(f"  Queries : {len(queries)}")
    print(f"  Top-K   : {args.top_k}")
    print(f"  DB      : {db_path.name}")

    for run in runs:
        print_report(run, args.top_k)

    # Summary comparison table if multiple modes
    if len(runs) > 1:
        print(f"\n{'='*60}")
        print("  CROSS-MODE SUMMARY")
        print(f"{'='*60}")
        print(f"{'Mode':<12} {'Recall@' + str(args.top_k):<12} {'MRR@' + str(args.top_k):<10} {'P95ms'}")
        print("-" * 45)
        for run in runs:
            r_vals = [r["recall"] for r in run["rows"] if r["recall"] is not None]
            m_vals = [r["mrr"]    for r in run["rows"] if r["mrr"]    is not None]
            avg_r  = sum(r_vals) / len(r_vals) if r_vals else None
            avg_m  = sum(m_vals) / len(m_vals) if m_vals else None
            print(
                f"{run['mode']:<12} "
                f"{_fmt(avg_r):<12} "
                f"{_fmt(avg_m):<10} "
                f"{p95(run['latencies']):.1f}"
            )

    save_csv(runs, Path(args.out))


if __name__ == "__main__":
    main()

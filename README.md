# HVDC Email Search v2.0

Streamlit + DuckDB email search platform for Samsung C&T HVDC project (Abu Dhabi).  
Live app: [sctemail-g8zv2taasbombiv4w9iz5s.streamlit.app](https://sctemail-g8zv2taasbombiv4w9iz5s.streamlit.app)

## Features

| Tab | Description |
|---|---|
| BM25 검색 | Full-text keyword search (subject / sender / body / HVDC cases) |
| 시맨틱 검색 | Vector similarity — all-MiniLM-L6-v2 (384 dim, no API key) |
| Analytics | Monthly heatmap, top senders, site/stage breakdown |
| 네트워크 | Email network graph |
| Anomaly | Unusual pattern alerts |
| Case Thread | Thread view by HVDC case number |

## Local Setup

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

### Build DB (one-time, ~60 min for 52k rows + embeddings)

Place `OUTLOOK_HVDC_*.xlsx` one level up (`Downloads/`), then:

```bash
python build_db.py
```

Produces `hvdc_mail.duckdb` with FTS + HNSW + 384-dim embeddings.

### Run locally

```bash
streamlit run app.py
# Open http://localhost:8501
```

## Cloud Deployment

The app downloads `hvdc_mail.duckdb` from **GitHub Releases v2.0** at startup.  
No Google API key required — semantic search runs via sentence-transformers on the server.

### Streamlit Cloud secrets (set in dashboard, not in git)

```toml
google_api_key = "..."   # optional — only for Gemini email summary
```

### Rebuild and redeploy

```bash
# 1. Rebuild DB locally
python build_db.py

# 2. Upload new DB as GitHub Release
gh release create v3.0 hvdc_mail.duckdb --title "v3.0 ..."

# 3. Update DB_URL in app.py line 14 to v3.0, commit, push
git add app.py && git commit -m "chore: bump DB_URL to v3.0"
git push origin main        # triggers Streamlit Cloud redeploy
```

## Architecture

```
app.py                  Streamlit UI + DuckDB read-only queries
build_db.py             Excel -> DuckDB + FTS + sentence-transformers embeddings + HNSW
requirements.txt        Runtime deps (Streamlit Cloud installs these)
requirements-dev.txt    Dev tools: pytest, ruff
.streamlit/
  config.toml           Theme (Samsung C&T navy)
  secrets.toml          API keys — gitignored, set in Streamlit Cloud dashboard
```

## DB Schema — emails table (51,964 rows)

Key columns: `no`, `subject`, `sendername`, `senderemail`, `deliverytime`,
`plaintextbody`, `hvdc_cases`, `company_name`, `site`, `stage`, `month`,
`embedding FLOAT[384]`

Indexes: B-tree (`idx_month`, `idx_stage`, `idx_site`),
HNSW cosine (`idx_embedding_hnsw`), BM25 FTS on 7 columns.

## Notes

- `hvdc_mail.duckdb` (448 MB) is gitignored — served via GitHub Releases.
- `OUTLOOK_HVDC_*.xlsx` is gitignored (sensitive internal data).
- Streamlit Cloud free tier: 1 GB RAM. Model loads ~5s on first semantic query.

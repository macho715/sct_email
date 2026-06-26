# HVDC Email Search

Streamlit + DuckDB full-text search app for HVDC Outlook export data.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

## Usage

```bash
# 1. Build DB (one-time, ~1 min for 50k rows)
python build_db.py

# 2. Launch app
streamlit run app.py
```

Open http://localhost:8501

## Features

- BM25 full-text search across Subject / SenderName / Body / HVDC Cases
- Sidebar filters: Month, Site, Stage, Sender email, Case number
- Email body viewer
- CSV export
- Analytics tab: monthly volume heatmap, top senders

## Data Source

`OUTLOOK_HVDC_20260626_120747 (2).xlsx` — place in the parent folder (`Downloads/`).

Headers on row 4, data from row 5.  27 columns, ~52k rows.

## Notes

- `hvdc_mail.duckdb` is excluded from git (`.gitignore`). Rebuild with `build_db.py`.
- FTS extension is installed on first run (requires write-mode connection, handled automatically).

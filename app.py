"""
HVDC Email Search — Streamlit + DuckDB  v2.0
Features: BM25 Search | Gemini AI Summary | Case Thread | Network Graph | Semantic Search
"""
import warnings
import requests
import duckdb
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

# ── DB 설정 ─────────────────────────────────────────────────────────
DB_URL   = "https://github.com/macho715/sct_email/releases/download/v2.1/hvdc_mail.duckdb"
DB_LOCAL = Path("/tmp/hvdc_mail_v21.duckdb")       # v2.1: multilingual embeddings
_DB_TMP  = Path("/tmp/hvdc_mail_v21.duckdb.tmp")   # path bump forces re-download

# ── 브랜드 색상 (Samsung C&T Navy) ──────────────────────────────────
_SEQ = [
    [0.0, "#EBF5FB"], [0.25, "#AED6F1"],
    [0.5,  "#5DADE2"], [0.75, "#2471A3"],
    [1.0,  "#1F5276"],
]
_CHART = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="system-ui, -apple-system, sans-serif", size=12),
    margin=dict(l=0, r=0, t=32, b=0),
)
_PIE_COLORS = [
    "#1F5276", "#2E86C1", "#5DADE2", "#A3E4D7",
    "#F4D03F", "#E67E22", "#A569BD", "#7F8C8D",
]

# ── 다국어 텍스트 ─────────────────────────────────────────────────────
_T = {
    "ko": {
        # page
        "caption": "OUTLOOK HVDC 전체 이메일 데이터 — DuckDB FTS · Gemini AI · Samsung C&T / ADNOC",
        # sidebar
        "label_search_filter": "검색 및 필터",
        "label_pdf_folders": "PDF 첨부파일 폴더",
        "kw_search": "키워드 검색 (FTS)",
        "kw_placeholder": "예: DSV, cable, 5000684244",
        "kw_help": "Subject · SenderName · Body · HVDC Cases 전체 텍스트 검색",
        "adv_filter": "고급 필터",
        "sender_filter_label": "발신자 이메일 포함",
        "sender_filter_ph": "@dsv.com",
        "case_filter_label": "HVDC Case 번호",
        "case_filter_ph": "HVDC-ADOPT-SEI-0008",
        "max_rows": "최대 결과 수",
        "db_diag": "DB 진단",
        "confirm_reset": "DB 재다운로드를 확인합니다 (기존 캐시가 모두 삭제됩니다)",
        "btn_reset": "캐시 초기화 + DB 재다운로드",
        # tabs
        "tab_search": "검색",
        "tab_analytics": "분석",
        "tab_semantic": "시맨틱 검색",
        # metrics
        "metric_match": "매칭 건수",
        "metric_match_help": "현재 필터 조건과 일치하는 이메일 수",
        "metric_shown": "표시 결과",
        "metric_shown_help": "최대",
        "metric_total": "DB 총 이메일",
        "metric_total_help": "전체 데이터베이스 보유량",
        # search tab
        "searching": "조회 중...",
        "no_results_filter": (
            "검색 결과가 없습니다.\n\n"
            "- 키워드 철자를 확인하거나 더 짧은 단어로 검색해보세요.\n"
            "- 필터 조건을 줄이면 더 많은 결과가 나올 수 있습니다."
        ),
        "no_results_empty": "왼쪽 사이드바에서 키워드 또는 필터를 입력하면 이메일을 검색합니다.",
        "col_subject": "제목",
        "col_sender": "발신자",
        "col_received": "수신일시",
        "col_recipients": "수신자",
        "col_body": "본문",
        "col_cases": "HVDC Cases",
        "col_score": "관련도",
        "col_pdf": "PDF",
        "email_detail": "본문 보기",
        "select_email": "메일 선택 (no 번호)",
        "detail_not_found": "선택한 메일 본문을 찾지 못했습니다. 검색을 다시 실행하거나 다른 메일을 선택해 주세요.",
        "btn_pdf": "첨부 PDF 열기 (Google Drive)",
        "btn_pdf_download": "PDF 다운로드",
        "pdf_folder_alt": "첨부 PDF 폴더 (날짜별로 분할 저장):",
        "pdf_quick_links": "PDF 빠른 열기",
        "btn_ai": "AI 요약 (Gemini)",
        "ai_spinner": "Gemini 분석 중...",
        "ai_no_key": "Gemini AI 요약을 사용하려면 Streamlit Secrets에 `google_api_key`를 추가하세요.",
        "case_thread": "케이스 스레드",
        "case_thread_count": "이 케이스 관련 이메일 총",
        "thread_timeline": "스레드 타임라인",
        "csv_download": "결과 CSV 다운로드",
        # analytics tab
        "metric_vol": "분석 이메일",
        "metric_peak": "피크 월",
        "analytics_csv": "Analytics CSV 다운로드",
        "subtab_vol": "📈 월별 추이",
        "subtab_heat": "🗺️ Site × 월 히트맵",
        "subtab_dist": "📊 Site / Stage 분포",
        "subtab_net": "🕸️ 네트워크",
        "vol_title": "월별 이메일 수신량",
        "vol_no_data": "월별 데이터가 없습니다.",
        "top_senders": "Top 20 발신 그룹",
        "raw_data": "월별 원시 데이터",
        "heat_title": "Site × 월 히트맵",
        "heat_no_data": "Site 또는 월 데이터가 없습니다.",
        "dist_title": "Site / Stage 분포",
        "site_no_data": "Site 데이터가 없습니다.",
        "stage_no_data": "Stage 데이터가 없습니다.",
        "net_title": "회사 이메일 네트워크",
        "net_caption": "발신 회사 → 수신 도메인 흐름 (5건 이상만 표시)",
        "net_no_data": "네트워크 데이터가 없습니다.",
        "net_fallback": "networkx 미설치 — 상위 연결 현황으로 대체 표시합니다. `pip install networkx`",
        "col_source": "발신 회사",
        "col_target": "수신 도메인",
        "col_weight": "이메일 수",
        "col_metric": "집계",
        "col_dim": "항목",
        "col_count": "이메일 수",
        # semantic tab
        "sem_title": "시맨틱 검색 (all-MiniLM-L6-v2, 384 dim)",
        "sem_no_emb": (
            "임베딩 데이터가 없습니다. 로컬에서 `build_db.py`를 실행하여 DB를 재빌드하세요:\n\n"
            "```bash\npython build_db.py\n```\n\n"
            "완료 후 GitHub Release에 v2.0으로 재업로드하고 `DB_URL`을 업데이트하세요."
        ),
        "sem_query_label": "의미 기반 검색어",
        "sem_query_ph": "예: transformer installation schedule delay",
        "sem_query_help": "정확한 키워드 대신 의미로 검색합니다",
        "sem_top_k": "결과 수",
        "sem_hybrid": "BM25 + 시맨틱 Hybrid (권장)",
        "sem_run": "시맨틱 검색 실행",
        "sem_embedding": "임베딩 생성 중...",
        "sem_searching": "벡터 검색 중...",
        "sem_no_result": "결과 없음 — 다른 검색어를 시도하거나 Hybrid 모드를 켜세요.",
        "sem_done": "검색 완료",
        "col_similarity": "유사도",
        "col_company": "회사",
        # axis / hover labels
        "axis_month": "연월",
        "axis_email_count": "이메일 수",
        "axis_sender_group": "발신 그룹",
        "axis_site": "Site",
        "axis_link": "연결",
        "connections": "연결 수",
        "db_init": "DB 초기화 중...",
        "db_ok": "DB 준비 완료!",
        "db_fail": "다운로드 실패",
        "db_err": "DB 다운로드 실패: ",
        "snip_header": "관련 본문 발췌",
        "snip_none": "(일치 문장 없음)",
        "col_snippet": "발췌",
        "sim_header": "유사 이메일 TOP 5",
        "sim_no_emb": "임베딩 데이터 없음 — 유사 검색 불가",
        "sim_searching": "유사 이메일 검색 중...",
        "col_sim_score": "유사도",
        "sem_translate": "검색어 확장 중...",
        "sem_translated": "번역된 검색어",
        "sem_no_key_translate": "Gemini API 키 없음 — 원문으로 검색합니다.",
        "bm25_translate": "한국어 감지 → 영어 번역 후 키워드 검색:",
        "btn_bulk_summary": "AI 일괄 요약 (상위 10건)",
        "bulk_summary_spinner": "Gemini 분석 중...",
        "bulk_summary_header": "검색 결과 AI 요약",
        "query_rewrite": "쿼리 확장 사용 (사전 + Gemini 옵션)",
        "query_rewrite_caption": "확장된 검색어:",
        "detected_entities": "감지된 항목",
        "col_entities": "항목",
        "col_match_reason": "검색 이유",
        "refine_placeholder": "결과 좁히기 (예: 2025년만, DSV만)",
        "btn_similar": "유사 이메일 5건",
        "btn_timeline": "Case 타임라인",
        "btn_sender_history": "발신자 히스토리",
        "btn_cluster": "이슈 유형 자동 분류",
        "cluster_header": "이슈 유형 분포",
        "btn_key_decisions": "핵심 결정 이메일 TOP 10",
        "key_decisions_header": "핵심 의사결정 이메일",
        "nl_query_placeholder": "자연어로 이메일 검색",
        "nl_query_caption": "Gemini가 SQL로 변환합니다 (예: 2025년 3월 Mammoet MRR)",
        "nl_query_header": "자연어 검색 결과",
    },
    "en": {
        # page
        "caption": "OUTLOOK HVDC Email Archive — DuckDB FTS · Gemini AI · Samsung C&T / ADNOC",
        # sidebar
        "label_search_filter": "Search & Filter",
        "label_pdf_folders": "PDF Attachment Folders",
        "kw_search": "Keyword Search (FTS)",
        "kw_placeholder": "e.g. DSV, cable, 5000684244",
        "kw_help": "Full-text search across Subject · SenderName · Body · HVDC Cases",
        "adv_filter": "Advanced Filter",
        "sender_filter_label": "Sender email contains",
        "sender_filter_ph": "@dsv.com",
        "case_filter_label": "HVDC Case No.",
        "case_filter_ph": "HVDC-ADOPT-SEI-0008",
        "max_rows": "Max results",
        "db_diag": "DB Diagnostics",
        "confirm_reset": "Confirm DB re-download (all cache will be cleared)",
        "btn_reset": "Clear Cache + Re-download DB",
        # tabs
        "tab_search": "Search",
        "tab_analytics": "Analytics",
        "tab_semantic": "Semantic Search",
        # metrics
        "metric_match": "Matched",
        "metric_match_help": "Emails matching current filter conditions",
        "metric_shown": "Shown",
        "metric_shown_help": "max",
        "metric_total": "Total Emails",
        "metric_total_help": "Total records in database",
        # search tab
        "searching": "Searching...",
        "no_results_filter": (
            "No results found.\n\n"
            "- Check spelling or try shorter keywords.\n"
            "- Reduce filter conditions to broaden results."
        ),
        "no_results_empty": "Enter a keyword or select filters in the left sidebar to search emails.",
        "col_subject": "Subject",
        "col_sender": "Sender",
        "col_received": "Received",
        "col_recipients": "Recipients",
        "col_body": "Body",
        "col_cases": "HVDC Cases",
        "col_score": "Relevance",
        "col_pdf": "PDF",
        "email_detail": "Email Detail",
        "select_email": "Select email (no)",
        "detail_not_found": "Could not find the selected email body. Refresh the search or choose another email.",
        "btn_pdf": "Open PDF Attachment (Google Drive)",
        "btn_pdf_download": "Download PDF",
        "pdf_folder_alt": "PDF Attachment Folders (split by date):",
        "pdf_quick_links": "PDF Quick Links",
        "btn_ai": "AI Summary (Gemini)",
        "ai_spinner": "Analysing with Gemini...",
        "ai_no_key": "Add `google_api_key` to Streamlit Secrets to enable Gemini AI summaries.",
        "case_thread": "Case Thread",
        "case_thread_count": "Total emails in this case",
        "thread_timeline": "Thread Timeline",
        "csv_download": "Download Results CSV",
        # analytics tab
        "metric_vol": "Total Emails",
        "metric_peak": "Peak Month",
        "analytics_csv": "Download Analytics CSV",
        "subtab_vol": "📈 Monthly Trend",
        "subtab_heat": "🗺️ Site × Month Heatmap",
        "subtab_dist": "📊 Site / Stage Distribution",
        "subtab_net": "🕸️ Network",
        "vol_title": "Monthly Email Volume",
        "vol_no_data": "No monthly data available.",
        "top_senders": "Top 20 Sender Groups",
        "raw_data": "Monthly Raw Data",
        "heat_title": "Site × Month Heatmap",
        "heat_no_data": "No site or monthly data available.",
        "dist_title": "Site / Stage Distribution",
        "site_no_data": "No site data available.",
        "stage_no_data": "No stage data available.",
        "net_title": "Company Email Network",
        "net_caption": "Sender company → Recipient domain flow (5+ emails only)",
        "net_no_data": "No network data available.",
        "net_fallback": "networkx not installed — showing top connections instead. `pip install networkx`",
        "col_source": "Sender Company",
        "col_target": "Recipient Domain",
        "col_weight": "Email Count",
        "col_metric": "Metric",
        "col_dim": "Dimension",
        "col_count": "Email Count",
        # semantic tab
        "sem_title": "Semantic Search (all-MiniLM-L6-v2, 384 dim)",
        "sem_no_emb": (
            "No embedding data found. Run `build_db.py` locally to rebuild the DB:\n\n"
            "```bash\npython build_db.py\n```\n\n"
            "Then re-upload to GitHub Release as v2.0 and update `DB_URL`."
        ),
        "sem_query_label": "Semantic search query",
        "sem_query_ph": "e.g. transformer installation schedule delay",
        "sem_query_help": "Search by meaning instead of exact keywords",
        "sem_top_k": "Results",
        "sem_hybrid": "BM25 + Semantic Hybrid (recommended)",
        "sem_run": "Run Semantic Search",
        "sem_embedding": "Generating embeddings...",
        "sem_searching": "Vector search in progress...",
        "sem_no_result": "No results — try different keywords or enable Hybrid mode.",
        "sem_done": "Search complete",
        "col_similarity": "Similarity",
        "col_company": "Company",
        # axis / hover labels
        "axis_month": "Month",
        "axis_email_count": "Email Count",
        "axis_sender_group": "Sender Group",
        "axis_site": "Site",
        "axis_link": "Link",
        "connections": "Connections",
        "db_init": "Initialising DB...",
        "db_ok": "DB ready!",
        "db_fail": "Download failed",
        "db_err": "DB download failed: ",
        "snip_header": "Matching Snippet",
        "snip_none": "(no match)",
        "col_snippet": "Snippet",
        "sim_header": "TOP 5 Similar Emails",
        "sim_no_emb": "No embedding — similarity search unavailable.",
        "sim_searching": "Finding similar emails...",
        "col_sim_score": "Similarity",
        "sem_translate": "Expanding query...",
        "sem_translated": "Translated query",
        "sem_no_key_translate": "No Gemini key — searching with original query.",
        "bm25_translate": "Korean detected → translated for FTS:",
        "btn_bulk_summary": "AI Summary (Top 10)",
        "bulk_summary_spinner": "Gemini summarizing...",
        "bulk_summary_header": "Search Results AI Summary",
        "query_rewrite": "Expand query (glossary + optional Gemini)",
        "query_rewrite_caption": "Expanded query:",
        "detected_entities": "Detected",
        "col_entities": "Entities",
        "col_match_reason": "Why matched",
        "refine_placeholder": "Refine results (e.g. 2025 only, DSV only)",
        "btn_similar": "Similar Emails (5)",
        "btn_timeline": "Case Timeline",
        "btn_sender_history": "Sender History",
        "btn_cluster": "Auto-Cluster by Issue Type",
        "cluster_header": "Issue Type Distribution",
        "btn_key_decisions": "Key Decision Emails TOP 10",
        "key_decisions_header": "Key Decision Emails",
        "nl_query_placeholder": "Natural language email search",
        "nl_query_caption": "Gemini converts to SQL (e.g. MRR from Mammoet in March 2025)",
        "nl_query_header": "Natural Language Query Results",
    },
}

# ─────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="HVDC Email Search",
    page_icon="✉",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 언어 상태 초기화 ──────────────────────────────────────────────────
if "lang" not in st.session_state:
    st.session_state.lang = "ko"
if "search_history" not in st.session_state:
    st.session_state.search_history = []

# ── 비밀번호 보호 ─────────────────────────────────────────────────────
_PASSWORD = st.secrets.get("password", "")
if _PASSWORD:
    _input_pwd = st.text_input("비밀번호를 입력하세요", type="password")
    if _input_pwd != _PASSWORD:
        st.warning("올바른 비밀번호를 입력해야 대시보드를 사용할 수 있습니다.")
        st.stop()

st.markdown("""
<style>
/* ─── LAYOUT ─── */
[data-testid="block-container"] { padding: 1rem 2rem 2rem !important; }

/* ─── HEADER BANNER ─── */
.hvdc-header {
    background: linear-gradient(135deg, #1F5276 0%, #2E86C1 55%, #5DADE2 100%);
    border-radius: 12px; padding: 18px 24px; margin-bottom: 1.2rem;
    display: flex; align-items: center; gap: 14px;
    box-shadow: 0 4px 20px rgba(31,82,118,0.25);
}
.hvdc-header-icon { font-size: 1.9rem; }
.hvdc-header-title {
    font-size: 1.5rem; font-weight: 700;
    color: #FFFFFF; margin: 0; letter-spacing: -0.02em;
}
.hvdc-header-caption { font-size: 0.78rem; color: rgba(255,255,255,0.80); margin: 3px 0 0; }
.hvdc-header-badge {
    margin-left: auto; background: rgba(255,255,255,0.15);
    border: 1px solid rgba(255,255,255,0.30); border-radius: 20px;
    padding: 4px 12px; font-size: 0.70rem;
    color: rgba(255,255,255,0.90); font-weight: 600; white-space: nowrap;
}

/* ─── SIDEBAR ─── */
[data-testid="stSidebar"] { background: #F0F4F8 !important; border-right: 1px solid #E2E8F0; }
[data-testid="stSidebar"] * { color: #1E293B !important; }
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stMultiSelect label,
[data-testid="stSidebar"] .stTextInput label,
[data-testid="stSidebar"] .stSlider label { color: #374151 !important; }
.sidebar-section {
    background: #FFFFFF; border: 1px solid #E2E8F0;
    border-radius: 10px; padding: 12px 14px; margin-bottom: 10px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
.sidebar-label {
    font-size: 0.68rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.10em; color: #1F5276; margin-bottom: 8px;
}

/* ─── METRIC CARDS ─── */
[data-testid="stMetric"] {
    background: #FFFFFF; border: 1px solid #E2E8F0;
    border-radius: 12px; padding: 14px 18px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    border-top: 3px solid #1F5276;
}
[data-testid="stMetricValue"] {
    color: #1F5276 !important; font-size: 1.6rem !important; font-weight: 700 !important;
}
[data-testid="stMetricLabel"] {
    font-size: 0.72rem !important; color: #64748B !important;
    font-weight: 600 !important; text-transform: uppercase; letter-spacing: 0.05em;
}

/* ─── TABS (pill style) ─── */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px; background: #F1F5F9; padding: 4px; border-radius: 10px;
}
.stTabs [role="tab"] {
    font-weight: 500; border-radius: 8px; padding: 6px 16px; color: #475569;
    transition: background 0.15s ease, color 0.15s ease;
}
.stTabs [role="tab"]:hover { background: rgba(31,82,118,0.08); color: #1F5276; }
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    background: #FFFFFF !important; color: #1F5276 !important;
    font-weight: 700; box-shadow: 0 1px 4px rgba(0,0,0,0.10); border-bottom: none !important;
}
.stTabs [data-baseweb="tab-highlight"] { display: none !important; }

/* ─── BUTTONS ─── */
.stButton > button { border-radius: 8px; font-weight: 600; transition: all 0.15s ease; }
.stButton > button:hover { transform: translateY(-1px); }
.stButton > button:focus-visible,
[data-testid="stDownloadButton"] > button:focus-visible { outline: 2px solid #1F5276; outline-offset: 2px; }
[data-testid="stDownloadButton"] > button {
    background: #1F5276; color: white; border: none;
    border-radius: 8px; padding: 0.45rem 1.1rem;
    font-weight: 600; transition: all 0.15s ease;
}
[data-testid="stDownloadButton"] > button:hover {
    background: #2E86C1; box-shadow: 0 3px 10px rgba(31,82,118,0.25); transform: translateY(-1px);
}

/* ─── TEXT INPUT ─── */
[data-testid="stTextInput"] input { border-radius: 8px !important; transition: border-color 0.15s !important; }
[data-testid="stTextInput"] input:focus {
    border-color: #1F5276 !important; box-shadow: 0 0 0 2px rgba(31,82,118,0.12) !important;
}

/* ─── DATA / ALERTS / EXPANDER / CHARTS ─── */
div[data-testid="stAlert"] { border-radius: 10px; border-left-width: 4px; }
[data-testid="stDataFrame"] { border-radius: 10px; border: 1px solid #E2E8F0; box-shadow: 0 1px 4px rgba(0,0,0,0.05); }
[data-testid="stExpander"] { border: 1px solid #E2E8F0 !important; border-radius: 10px !important; overflow: hidden; }
[data-testid="stPlotlyChart"] { border: 1px solid #E2E8F0; border-radius: 12px; overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,0.05); }

/* ─── AI SUMMARY CARD ─── */
.ai-summary-card {
    background: linear-gradient(to right, #EBF5FB, #F8FBFF);
    border-left: 4px solid #1F5276; border-radius: 0 10px 10px 0;
    padding: 16px 20px; margin-top: 10px; white-space: pre-wrap;
    font-size: 0.88rem; line-height: 1.7; color: #1E293B;
    box-shadow: 0 2px 8px rgba(31,82,118,0.08);
}

/* ─── EMAIL CARD ─── */
.email-card {
    background: #FFFFFF; border: 1px solid #E2E8F0;
    border-radius: 10px; padding: 14px 18px; margin-bottom: 8px;
    transition: box-shadow 0.15s ease, border-color 0.15s ease;
}
.email-card:hover { box-shadow: 0 4px 16px rgba(31,82,118,0.12); border-color: #5DADE2; }
.email-card-subject { font-weight: 600; font-size: 0.95rem; color: #1E293B; margin-bottom: 4px; }
.email-card-meta { font-size: 0.78rem; color: #64748B; display: flex; gap: 10px; }
.email-card-snippet { margin-top: 8px; font-size: 0.82rem; color: #475569; border-top: 1px solid #F1F5F9; padding-top: 8px; line-height: 1.5; }

/* ─── TAGS / BADGES ─── */
.tag-pill {
    display: inline-block; background: #EBF5FB; color: #1F5276;
    border: 1px solid #AED6F1; border-radius: 20px;
    font-size: 0.68rem; font-weight: 600; padding: 1px 8px; margin: 2px;
}
.score-badge {
    display: inline-block; background: #1F5276; color: white;
    border-radius: 6px; font-size: 0.66rem; font-weight: 700; padding: 2px 7px; vertical-align: middle;
}

/* ─── MISC ─── */
.lang-toggle button { font-size: 0.8rem !important; font-weight: 700 !important; padding: 0.25rem 0.5rem !important; }
hr { border-color: #E2E8F0 !important; margin: 10px 0 !important; }
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #F1F5F9; border-radius: 3px; }
::-webkit-scrollbar-thumb { background: #CBD5E1; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #94A3B8; }

/* ─── MOBILE OPTIMIZATIONS (ui-ux-pro-max P1/P2/P5) ─── */
/* P1: iOS auto-zoom prevention — input font-size must be ≥16px */
input, textarea, [data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea { font-size: 16px !important; }
/* P2: Touch targets ≥44px */
.stButton > button { min-height: 44px !important; padding: 0 1rem !important; }
.stTabs [role="tab"] { min-height: 44px !important; }
[data-testid="stDownloadButton"] > button { min-height: 44px !important; }
/* P5: Mobile layout — keep sidebar controls available on phones */
@media (max-width: 768px) {
    [data-testid="block-container"] { padding: 0.75rem 0.75rem 1rem !important; }
    .hvdc-header { padding: 12px 14px !important; }
    .hvdc-header-title { font-size: 1.1rem !important; }
    .hvdc-header-badge { display: none !important; }
}
</style>
""", unsafe_allow_html=True)


# ── DB 연결 (다운로드는 top-level에서 처리) ──────────────────────────
@st.cache_resource
def _ensure_fts_extension():
    if not DB_LOCAL.exists():
        return

    tmp = duckdb.connect(str(DB_LOCAL))
    try:
        try:
            tmp.execute("INSTALL fts;")
        except Exception as _e:
            warnings.warn(f"FTS INSTALL skipped: {_e}")
        tmp.execute("LOAD fts;")
    finally:
        tmp.close()


@st.cache_resource
def get_con():
    _ensure_fts_extension()
    con = duckdb.connect(str(DB_LOCAL), read_only=True)
    con.execute("LOAD fts;")
    try:
        con.execute("LOAD vss;")
    except Exception:
        pass
    return con


def run_query(sql: str, params=None) -> pd.DataFrame:
    con = get_con()
    try:
        if params:
            return con.execute(sql, params).df()
        return con.execute(sql).df()
    except Exception as e:
        st.error(f"Query error: {e}")
        return pd.DataFrame()


def _clean_month(series: pd.Series) -> pd.Series:
    return series.astype(str).str.replace(r"\.0$", "", regex=True).str.strip()


def _clean_id_value(value) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text.endswith(".0"):
        return text[:-2]
    return text


def _id_lookup_where(column: str = "no") -> str:
    normalized = f"regexp_replace(CAST({column} AS VARCHAR), '\\.0+$', '')"
    return f"(CAST({column} AS VARCHAR) = ? OR {normalized} = ?)"


def _id_lookup_params(value) -> list[str]:
    if pd.isna(value):
        return ["", ""]
    raw = str(value).strip()
    return [raw, _clean_id_value(raw)]


def _clean_id_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in ["no", "month"]:
        if col in out.columns:
            out[col] = out[col].apply(_clean_id_value)
    return out


# ── 필터 옵션 로드 ────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_filter_options():
    con = get_con()
    months = [r[0] for r in con.execute(
        "SELECT DISTINCT month FROM emails WHERE month IS NOT NULL ORDER BY month"
    ).fetchall()]
    months = [str(m).replace(".0", "") for m in months]
    sites  = [r[0] for r in con.execute(
        "SELECT DISTINCT site  FROM emails WHERE site  IS NOT NULL ORDER BY site"
    ).fetchall()]
    stages = [r[0] for r in con.execute(
        "SELECT DISTINCT stage FROM emails WHERE stage IS NOT NULL ORDER BY stage"
    ).fetchall()]
    return months, sites, stages


@st.cache_data(ttl=300)
def count_emails(where_clause: str = "", params: tuple = ()) -> int:
    sql = f"SELECT COUNT(*) FROM emails {where_clause}"
    df = run_query(sql, list(params) if params else None)
    return int(df.iloc[0, 0]) if not df.empty else 0


@st.cache_data(ttl=3600)
def email_columns() -> tuple[str, ...]:
    df = run_query(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name='emails'"
    )
    if df.empty or "column_name" not in df.columns:
        return tuple()
    return tuple(str(v) for v in df["column_name"].tolist())


def get_total_emails() -> int:
    return count_emails()


# ── Feature 1: Gemini 요약 ────────────────────────────────────────
@st.cache_data(ttl=1800, show_spinner=False)
def summarize_with_gemini(subject: str, body: str, api_key: str) -> str:
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        prompt = f"""다음 HVDC 프로젝트 이메일을 한국어로 요약하세요.
형식:
• 목적: (1줄)
• 핵심 정보: (수치·날짜·자재명 포함, 최대 3줄)
• 액션 아이템: (☐ 형식, 없으면 "없음")

제목: {subject}
본문:
{str(body or '')[:3000]}"""
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return resp.text
    except Exception as e:
        msg = str(e)
        if "429" in msg or "RESOURCE_EXHAUSTED" in msg or "spending cap" in msg:
            return "Gemini API monthly quota exceeded. Visit https://aistudio.google.com/app/apikey to raise the limit or retry next month."
        return f"Error: {e}"


# ── Feature 2: 시맨틱 검색 (sentence-transformers all-MiniLM-L6-v2, 384 dim) ─
@st.cache_resource(show_spinner=False)
def _get_st_model():
    from sentence_transformers import SentenceTransformer
    # Multilingual (50+ langs incl. Korean), 384d — matches build_db.py EMBED_MODEL.
    # Korean queries embed natively; no Korean→English translation needed.
    return SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")


def get_query_embedding(query: str, api_key: str = ""):
    try:
        model = _get_st_model()
        vec = model.encode([query], normalize_embeddings=True)[0].tolist()
        return vec
    except Exception as e:
        st.error(f"Embedding error: {e}")
        return None


def has_embeddings() -> bool:
    try:
        df = run_query(
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_name='emails' AND column_name='embedding'"
        )
        if df.empty or int(df.iloc[0, 0]) == 0:
            return False
        cnt = run_query("SELECT COUNT(*) FROM emails WHERE embedding IS NOT NULL")
        return not cnt.empty and int(cnt.iloc[0, 0]) > 0
    except Exception:
        return False


def _query_terms(query: str) -> list[str]:
    import re
    stopwords = {"or", "and", "the", "with", "for", "from"}
    terms = []
    for term in re.findall(r"[A-Za-z0-9가-힣][A-Za-z0-9가-힣/\-]{1,}", query or ""):
        t = term.strip()
        if len(t) > 2 and t.lower() not in stopwords:
            terms.append(t)
    return list(dict.fromkeys(terms))


def _mask_sensitive_text(text: str) -> str:
    import re
    masked = re.sub(
        r"\b[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}\b",
        "[email]",
        text or "",
        flags=re.IGNORECASE,
    )
    masked = re.sub(r"\+?\d[\d\s().\-]{7,}\d", "[phone/ref]", masked)
    masked = re.sub(r"\b[A-Z]{1,5}[-:/ ]?\d{5,}[A-Z0-9\-/]*\b", "[ref]", masked, flags=re.IGNORECASE)
    masked = re.sub(r"\b\d{8,}\b", "[ref]", masked)
    return masked


def _mask_entity_value(tag: str, value: str) -> str:
    if tag in {"Ref", "BL", "PO", "Case"}:
        return _mask_sensitive_text(value)
    return str(value).strip()


def _extract_snippet(body: str, query: str, context_chars: int = 150) -> str:
    if not body or not query:
        return ""
    import re
    terms = _query_terms(query)
    if not terms:
        return ""

    compact = re.sub(r"\s+", " ", str(body)).strip()
    sentences = [
        s.strip()
        for s in re.split(r"(?<=[.!?。！？])\s+|[\r\n]+", compact)
        if s.strip()
    ]
    if not sentences:
        sentences = [compact]

    scored = []
    lower_terms = [t.lower() for t in terms]
    for idx, sentence in enumerate(sentences):
        sent_lower = sentence.lower()
        score = sum(2 if t in sent_lower else 0 for t in lower_terms)
        if score:
            score += max(0, 2 - idx * 0.1)
            scored.append((score, idx, sentence))

    if scored:
        picked = [s for _, _, s in sorted(scored, key=lambda x: (-x[0], x[1]))[:3]]
        snippet = " ".join(picked)
    else:
        body_lower = compact.lower()
        best_pos = min(
            [body_lower.find(t) for t in lower_terms if body_lower.find(t) != -1],
            default=-1,
        )
        if best_pos == -1:
            return ""
        start = max(0, best_pos - context_chars)
        end = min(len(compact), best_pos + context_chars)
        snippet = ("..." if start > 0 else "") + compact[start:end] + ("..." if end < len(compact) else "")

    snippet = _mask_sensitive_text(snippet)
    for term in terms:
        snippet = re.sub(f"(?i)({re.escape(term)})", r"**\1**", snippet)
    return snippet


_ENTITY_PATTERNS = {
    "Site": r"\b(?:AGI|DAS|MIR|SHU|MOSB)\b",
    "Vendor": r"\b(?:DSV|Mammoet|ADNOC|ALS|SCT|Samsung C&T|HMM|COSCO)\b",
    "Doc": r"\b(?:BL|B/L|BOE|DO|MRR|CIPL|FANR|Invoice|Packing List|Purchase Order)\b",
    "Issue": r"\b(?:DEM|DET|demurrage|detention|claim|delay|delayed|hold|customs clearance|통관|지연|클레임|디머리지|디텐션|승인|보류)\b",
    "Ref": r"\b(?:HVDC|CASE|PO|BL|BOE|MRR|FANR|INV)[-:/\s]?[A-Z0-9][A-Z0-9\-/]{4,}\b|\b\d{8,}\b",
}


def _extract_entities(text: str) -> dict:
    import re
    found = {}
    for tag, pattern in _ENTITY_PATTERNS.items():
        values = []
        for m in re.finditer(pattern, text or "", re.IGNORECASE):
            val = _mask_entity_value(tag, m.group(0))
            if val and val not in values:
                values.append(val)
        if values:
            found[tag] = values[:6]
    return found


def _merge_entities(*entity_maps: dict) -> dict:
    merged = {}
    for entity_map in entity_maps:
        for tag, values in (entity_map or {}).items():
            bucket = merged.setdefault(tag, [])
            for val in values:
                if val not in bucket:
                    bucket.append(val)
    return {tag: values[:6] for tag, values in merged.items() if values}


def _entity_chip_text(entities: dict) -> str:
    parts = []
    for tag in ["Vendor", "Issue", "Site", "Doc", "Ref", "BL", "PO", "Case"]:
        vals = entities.get(tag) or []
        if vals:
            parts.append(f"[{tag}: {', '.join(vals[:3])}]")
    return " ".join(parts)


def _normalize_score(series: pd.Series) -> pd.Series:
    vals = pd.to_numeric(series, errors="coerce").fillna(0.0)
    if vals.empty:
        return vals
    hi = float(vals.max())
    lo = float(vals.min())
    if hi == lo:
        return pd.Series([1.0 if hi else 0.0] * len(vals), index=vals.index)
    return (vals - lo) / (hi - lo)


def _rrf_score(series: pd.Series, *, ascending: bool = False, k: int = 60) -> pd.Series:
    vals = pd.to_numeric(series, errors="coerce")
    valid = vals.notna()
    scores = pd.Series(0.0, index=vals.index)
    if not valid.any():
        return scores
    ranks = vals[valid].rank(method="min", ascending=ascending)
    scores.loc[valid] = 1.0 / (k + ranks)
    return scores


def _identifier_terms(query: str) -> list[str]:
    import re
    text = str(query or "").strip()
    candidates: list[str] = []
    patterns = [
        r"\b\d{4,}\b",
        r"\b[A-Z0-9]{2,}(?:[-_/][A-Z0-9]+)+\b",
        r"\b[A-Z]{1,10}\d[A-Z0-9/-]{3,}\b",
        r"\b(?:HVDC|CASE|PO|BL|BOE|MRR|FANR|INV)[-:/\s]?[A-Z0-9][A-Z0-9\-/]{4,}\b",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            val = re.sub(r"\s+", " ", match.group(0)).strip(" ,.;:()[]{}")
            if val:
                candidates.append(val)
    for term in _query_terms(text):
        if any(ch.isdigit() for ch in term) or "-" in term or "/" in term:
            candidates.append(term)
    return list(dict.fromkeys(candidates))[:8]


def _is_identifier_query(query: str) -> bool:
    return bool(_identifier_terms(query))


def _field_hit_reason(row: pd.Series, query: str) -> str:
    terms = _identifier_terms(query) or _query_terms(query)
    if not terms:
        return ""
    fields = [
        ("no", "no"),
        ("hvdc_cases", "case"),
        ("primary_case", "case"),
        ("case_numbers", "case"),
        ("lpo_numbers", "lpo"),
        ("subject", "subject"),
        ("senderemail", "sender"),
        ("company_name", "company"),
        ("linkkey", "pdf"),
        ("rowkey", "rowkey"),
    ]
    reasons = []
    for term in terms[:6]:
        t = str(term).lower()
        for col, label in fields:
            if t and t in str(row.get(col, "") or "").lower():
                reasons.append(f"{label}:{term}")
                break
    return ", ".join(list(dict.fromkeys(reasons))[:4])


def _field_match_score(row: pd.Series, query: str) -> float:
    terms = [str(t).lower() for t in (_identifier_terms(query) or _query_terms(query))[:6]]
    if not terms:
        return 0.0
    weighted_fields = [
        ("hvdc_cases", 0.35),
        ("primary_case", 0.35),
        ("case_numbers", 0.35),
        ("lpo_numbers", 0.30),
        ("subject", 0.25),
        ("senderemail", 0.15),
        ("company_name", 0.15),
        ("linkkey", 0.10),
        ("rowkey", 0.25),
    ]
    score = 0.0
    for col, weight in weighted_fields:
        text = str(row.get(col, "") or "").lower()
        if text and any(term in text for term in terms):
            score += weight
    return min(1.0, score)


def _exact_match_tier(row: pd.Series, terms: list[str]) -> int:
    clean_terms = {_clean_id_value(t).lower() for t in terms if _clean_id_value(t)}
    no_value = _clean_id_value(row.get("no", "")).lower()
    if no_value and no_value in clean_terms:
        return 0
    strong_fields = [
        "hvdc_cases", "primary_case", "case_numbers", "lpo_numbers",
        "subject", "linkkey", "rowkey", "senderemail", "company_name",
    ]
    for col in strong_fields:
        text = str(row.get(col, "") or "").lower()
        if text and any(term.lower() in text for term in terms):
            return 1
    return 2


def _entity_match_score(row: pd.Series, query_entities: dict, query: str) -> float:
    haystack = " ".join(
        str(row.get(col, "") or "")
        for col in ["subject", "sendername", "senderemail", "company_name", "site", "stage", "hvdc_cases"]
    ).lower()
    hits = 0
    total = 0
    for values in (query_entities or {}).values():
        for value in values[:4]:
            total += 1
            if value and str(value).lower() in haystack:
                hits += 1
    for term in _query_terms(query)[:6]:
        total += 1
        if term.lower() in haystack:
            hits += 1
    return min(1.0, hits / max(total, 1))


def _decision_signal_score(row: pd.Series) -> float:
    text = " ".join(str(row.get(col, "") or "") for col in ["subject", "hvdc_cases"]).lower()
    signals = [
        "approve", "approved", "approval", "confirm", "confirmed", "reject",
        "rejected", "hold", "pending", "claim", "decision", "승인", "확정", "보류", "클레임",
    ]
    return 1.0 if any(sig in text for sig in signals) else 0.0


def _search_copilot_rerank(df: pd.DataFrame, query: str, query_entities: dict | None = None) -> pd.DataFrame:
    if df.empty or not query:
        return df

    out = df.copy()
    query_entities = query_entities or _extract_entities(query)
    if "bm25_norm" not in out.columns:
        out["bm25_norm"] = _normalize_score(out["bm25_score"]) if "bm25_score" in out.columns else 0.0
    out["vector_norm"] = _normalize_score(out["cosine_score"]) if "cosine_score" in out.columns else 0.0
    out["entity_match"] = out.apply(lambda row: _entity_match_score(row, query_entities, query), axis=1)
    dt = pd.to_datetime(out.get("deliverytime"), errors="coerce")
    if dt.notna().any():
        age_days = (dt.max() - dt).dt.days.fillna(9999)
        out["recency_score"] = 1 - _normalize_score(age_days)
    else:
        out["recency_score"] = 0.0
    out["decision_signal"] = out.apply(_decision_signal_score, axis=1)
    if "exact_score" in out.columns:
        out["exact_score"] = pd.to_numeric(out["exact_score"], errors="coerce").fillna(0.0)
    else:
        out["exact_score"] = pd.Series(0.0, index=out.index)
    out["field_match"] = out.apply(lambda row: _field_match_score(row, query), axis=1)
    bm25_rrf = _rrf_score(out["bm25_score"]) if "bm25_score" in out.columns else 0.0
    vector_rrf = _rrf_score(out["cosine_score"]) if "cosine_score" in out.columns else 0.0
    exact_rrf = _rrf_score(out["exact_rank"], ascending=True) if "exact_rank" in out.columns else 0.0
    out["search_copilot_score"] = (
        10.0 * bm25_rrf
        + 8.0 * vector_rrf
        + 8.0 * exact_rrf
        + 0.50 * out["exact_score"].clip(0.0, 1.0)
        + 0.12 * out["field_match"]
        + 0.12 * out["entity_match"]
        + 0.05 * out["recency_score"]
        + 0.05 * out["decision_signal"]
    )
    if "match_reason" not in out.columns:
        out["match_reason"] = ""
    field_reason = out.apply(lambda row: _field_hit_reason(row, query), axis=1)
    out["match_reason"] = [
        ", ".join(list(dict.fromkeys([part for part in [base, extra] if part]))[:4])
        for base, extra in zip(out["match_reason"].fillna(""), field_reason)
    ]
    return out.sort_values("search_copilot_score", ascending=False)


def _deterministic_rewrite_query(text: str) -> str:
    terms = _query_terms(text)
    expanded = list(terms)
    q_lower = (text or "").lower()

    for key, (variants, en_terms) in HVDC_GLOSSARY.items():
        candidates = [key, *variants, *en_terms]
        if any(str(c).lower() in q_lower for c in candidates):
            expanded.extend(en_terms[:3])

    direct_map = {
        "dem": ["DEM", "demurrage", "detention"],
        "det": ["DET", "detention", "demurrage"],
        "claim": ["claim", "dispute", "supporting invoice"],
        "delay": ["delay", "delayed", "hold"],
        "boe": ["BOE", "bill of entry", "customs declaration"],
        "mrr": ["MRR", "material receiving report", "inspection"],
    }
    for key, synonyms in direct_map.items():
        if key in q_lower:
            expanded.extend(synonyms)

    normalized = []
    for term in expanded:
        term = str(term).strip()
        if term and term.lower() not in {x.lower() for x in normalized}:
            normalized.append(term)
    return " OR ".join(normalized[:5]) if normalized else (text or "")


def _rewrite_query(text: str, api_key: str) -> str:
    """Expand query deterministically first, then optionally ask Gemini for close synonyms."""
    deterministic = _deterministic_rewrite_query(text)
    if not api_key:
        return deterministic
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=(
                "You are a logistics email search assistant. "
                "Add at most 2 closely related synonyms to the query below. "
                "Only add synonyms that are genuinely related to this specific term — "
                "do NOT add generic domain terms or acronyms that are unrelated. "
                "Format: original OR synonym1 OR synonym2. "
                "If no close synonym exists, return the original unchanged. "
                "Return ONLY the query, no explanation:\n\n" + deterministic
            ),
        )
        result = resp.text.strip()
        # Safety guard: if Gemini returns >4 OR-terms, it over-expanded — fall back
        if len(result.split(" OR ")) > 5:
            return deterministic
        return result
    except Exception:
        return deterministic


def _translate_ko_to_en(text: str, api_key: str) -> str:
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=(
                "Translate this Korean word or phrase to English. "
                "Return ONLY the direct translation — one short phrase, no synonyms, "
                "no explanations, no OR-joined alternatives:\n\n" + text
            ),
        )
        result = resp.text.strip()
        # Safety guard: if translation contains multiple OR-terms, it over-expanded
        if " OR " in result and len(result.split(" OR ")) > 2:
            return text
        return result
    except Exception:
        return text


def _is_korean(text: str) -> bool:
    return any("가" <= ch <= "힣" for ch in text)


@st.cache_resource(show_spinner=False)
def _drive_links() -> dict:
    """linkkey(12-hex prefix) → list of {id, title} Drive PDF files.

    Built by enumerating the 5 shared attachment folders (files named
    '{linkkey}_{name}.pdf'). A linkkey maps to MULTIPLE files when the
    attachment was split (part1/part2/...). Emails without an uploaded PDF
    return [] and fall back to folder browse links.
    """
    import json
    from pathlib import Path
    try:
        with open(Path(__file__).parent / "drive_links.json", encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception:
        return {}


def _pdf_parts(linkkey) -> list:
    """Direct Drive links for a linkkey's PDF(s) as (label, url) tuples.

    Uses /file/d/{id}/view (works for any link-shared viewer) instead of
    /drive/search?q= which only resolves for the owner when logged in.
    Split attachments yield "part 1/2/…" labels. Returns [] when no PDF
    exists → caller shows the folder-browse fallback.
    """
    if not linkkey:
        return []
    items = _drive_links().get(str(linkkey).strip()) or []
    multi = len(items) > 1
    out = []
    for i, it in enumerate(items, 1):
        file_id = str(it.get("id", "")).strip()
        if not file_id:
            continue
        url = _drive_view_url(file_id)
        out.append((f"📄 PDF part {i}" if multi else "📄 PDF", url))
    return out


def _drive_items_for_email(*values) -> list[dict]:
    """Find exact PDF matches by linkkey or Drive file URL in email fields."""
    import re

    links = _drive_links()
    candidates: list[str] = []
    drive_ids: list[str] = []
    for value in values:
        if value is None or pd.isna(value):
            continue
        text = str(value).strip()
        if text.lower() in ("", "none", "nan", "null"):
            continue
        candidates.append(text)
        candidates.extend(re.findall(r"\b[0-9a-fA-F]{12}\b", text))
        drive_ids.extend(
            re.findall(
                r"(?:drive\.google\.com/file/d/|[?&]id=)([A-Za-z0-9_-]{20,})",
                text,
            )
        )

    seen_keys = set()
    for key in candidates:
        clean_key = key.strip()
        if clean_key in seen_keys:
            continue
        seen_keys.add(clean_key)
        items = links.get(clean_key)
        if items:
            return items

    out = []
    seen_ids = set()
    for file_id in drive_ids:
        if file_id in seen_ids:
            continue
        seen_ids.add(file_id)
        out.append({"id": file_id, "title": "Google Drive PDF"})
    return out


def _pdf_parts_for_email(*values) -> list:
    items = _drive_items_for_email(*values)
    multi = len(items) > 1
    out = []
    for i, it in enumerate(items, 1):
        file_id = str(it.get("id", "")).strip()
        if not file_id:
            continue
        out.append((f"📄 PDF part {i}" if multi else "📄 PDF", _drive_view_url(file_id)))
    return out


def _pdf_download_parts_for_email(*values) -> list:
    items = _drive_items_for_email(*values)
    multi = len(items) > 1
    out = []
    for i, it in enumerate(items, 1):
        file_id = str(it.get("id", "")).strip()
        if not file_id:
            continue
        out.append((f"PDF part {i}" if multi else "PDF", _drive_download_url(file_id)))
    return out


def _drive_view_url(file_id: str) -> str:
    return f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"


def _drive_download_url(file_id: str) -> str:
    return f"https://drive.google.com/uc?export=download&id={file_id}"


def _pdf_download_parts(linkkey) -> list:
    """Direct Drive download links for mobile browsers that do not open viewer links."""
    if not linkkey:
        return []
    items = _drive_links().get(str(linkkey).strip()) or []
    multi = len(items) > 1
    out = []
    for i, it in enumerate(items, 1):
        file_id = str(it.get("id", "")).strip()
        if not file_id:
            continue
        out.append((f"PDF part {i}" if multi else "PDF", _drive_download_url(file_id)))
    return out


def _pdf_url(linkkey) -> str:
    """First PDF link for a linkkey (table column), or '' when none."""
    parts = _pdf_parts(linkkey)
    return parts[0][1] if parts else ""


def _pdf_download_url(linkkey) -> str:
    """First PDF download link for a linkkey (table column), or '' when none."""
    parts = _pdf_download_parts(linkkey)
    return parts[0][1] if parts else ""


# HVDC 물류 도메인 용어 사전 — 한국어 키워드 → (한국어 변형들, 영어 BM25 동의어들)
# HVDC 어휘는 고정 집합이므로 결정론적 사전이 Gemini 직역보다 정확·무료·즉시.
# 운영 빈도순. 미스 시 호출부에서 원문 직역으로 폴백.
HVDC_GLOSSARY: dict[str, tuple[list[str], list[str]]] = {
    "디머리지": (["디머리지", "DEM", "demurrage"],          ["DEM", "demurrage", "detention"]),
    "디텐션":   (["디텐션", "DET", "detention"],            ["DET", "detention", "demurrage"]),
    "dem":      (["DEM", "디머리지", "demurrage"],          ["DEM", "demurrage", "detention"]),
    "det":      (["DET", "디텐션", "detention"],            ["DET", "detention", "demurrage"]),
    "클레임":   (["클레임", "claim", "분쟁"],               ["claim", "dispute", "supporting invoice"]),
    "기성":   (["기성", "기성금", "기성청구", "기성고"], ["progress payment", "interim payment", "IPC"]),
    "통관":   (["통관", "수입통관", "세관"],              ["customs clearance", "customs"]),
    "선적":   (["선적", "적재", "본선적재"],              ["shipment", "shipping", "loading"]),
    "하역":   (["하역", "양하", "양륙"],                  ["discharge", "unloading", "offloading"]),
    "지연":   (["지연", "딜레이", "지체"],                ["delay", "delayed", "demurrage", "detention"]),
    "정산":   (["정산", "정산서", "비용정산"],            ["settlement", "reconciliation"]),
    "검사":   (["검사", "검수", "수입검사"],              ["inspection", "MRR", "material receiving report"]),
    "송장":   (["송장", "인보이스", "청구서"],            ["invoice", "billing"]),
    "납품":   (["납품", "납기", "납품서"],                ["delivery", "delivery note", "DN"]),
    "발주":   (["발주", "구매발주", "발주서"],            ["purchase order", "PO"]),
    "운송":   (["운송", "수송", "내륙운송"],              ["transport", "transportation", "trucking"]),
    "보관":   (["보관", "창고보관", "장치"],              ["storage", "warehouse", "warehousing"]),
    "통보":   (["통보", "통지", "공지"],                  ["notice", "notification"]),
    "승인":   (["승인", "결재", "허가"],                  ["approval", "approved"]),
    "계약":   (["계약", "계약서", "약정"],                ["contract", "agreement"]),
    "견적":   (["견적", "견적서", "가격"],                ["quotation", "quote"]),
    "포장":   (["포장", "패킹", "포장명세"],              ["packing", "packing list"]),
    "통선":   (["통선", "부선", "바지"],                  ["barge", "feeder vessel"]),
    "중량물": (["중량물", "초중량", "대형화물"],          ["heavy lift", "heavy cargo", "oversized"]),
    "면장":   (["면장", "수입면장", "통관면장"],          ["customs declaration", "bill of entry", "BOE"]),
    "fanr":    (["FANR", "fanr"],                          ["FANR", "approval", "notice"]),
    "mrr":     (["MRR", "mrr", "검수"],                    ["MRR", "material receiving report", "inspection"]),
}


def _glossary_expand(ko_query: str) -> tuple[list[str], list[str]]:
    """한국어 쿼리 → (한국어 변형들, 영어 BM25 동의어들).

    사전 매칭(부분 포함) 시 모든 관련 변형·영어 동의어 반환.
    매칭 없으면 ([원문], []) — 호출부는 영어 비어있으면 ILIKE 단독으로 폴백.
    """
    q = ko_query.strip()
    q_lower = q.lower()
    ko_out = [q]
    en_out: list[str] = []
    for key, (ko_variants, en_terms) in HVDC_GLOSSARY.items():
        candidates = [key, *ko_variants, *en_terms]
        if any(str(c).lower() in q_lower for c in candidates):
            ko_out.extend(ko_variants)
            en_out.extend(en_terms)
    ko_out = list(dict.fromkeys(v for v in ko_out if v))
    en_out = list(dict.fromkeys(v for v in en_out if v))
    return (ko_out[:8], en_out[:8])


def _cluster_emails(df):
    """Keyword-based issue clustering — no API cost."""
    _CLUSTERS = {
        "DEM/DET": ["demurrage", "detention", "dem/det", " dem ", " det "],
        "통관": ["customs", "clearance", "통관", "boe", "duty", "tariff"],
        "선적지연": ["delay", "delayed", "postpone", "reschedule", "선적지연", "지연"],
        "MOSB": ["mosb", "mother ship", "offshore"],
        "MRR": ["mrr", "material receipt", "receiving report"],
    }

    def _label(row):
        text = (str(row.get("subject", "")) + " " + str(row.get("hvdc_cases", ""))).lower()
        for cluster, kws in _CLUSTERS.items():
            if any(kw in text for kw in kws):
                return cluster
        return "기타"

    df = df.copy()
    df["issue_type"] = df.apply(_label, axis=1)
    return df


def _key_decisions_query():
    """BM25 FTS for decision-related emails, no API cost."""
    _kw = "승인 결정 confirm approve reject decision"
    return run_query(
        "SELECT no, deliverytime, subject, sendername, company_name, hvdc_cases "
        "FROM emails "
        "WHERE fts_main_emails.match_bm25(no, ?) IS NOT NULL "
        "ORDER BY deliverytime DESC LIMIT 10",
        [_kw],
    )


def _nl_to_sql(text: str, api_key: str):
    """Natural language → parameterized SQL WHERE clause via Gemini Flash.
    Returns (where_clause, params) or ('', []) on failure.
    """
    _ALLOWED_COLS = {
        "deliverytime", "sendername", "senderemail", "company_name",
        "site", "stage", "month", "hvdc_cases", "subject",
    }
    try:
        import json as _json
        import re as _re
        from google import genai as _genai
        _client = _genai.Client(api_key=api_key)
        _sys = (
            "SQL WHERE clause generator for HVDC email database. "
            f"Allowed columns: {sorted(_ALLOWED_COLS)}. "
            'Return JSON only: {"where": "col OPERATOR ?", "params": ["val"]}. '
            "Use ? placeholders for all values. ILIKE for text (add % to param). "
            "BETWEEN for date ranges with two params. "
            'Impossible: {"where": "", "params": []}. No markdown.'
        )
        _resp = _client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"{_sys}\n\nRequest: {text}",
        )
        _m = _re.search(r'\{.*?\}', _resp.text.strip(), _re.DOTALL)
        if not _m:
            return "", []
        _obj = _json.loads(_m.group())
        _where = str(_obj.get("where", ""))
        _params = list(_obj.get("params", []))
        _where_upper = _where.upper()
        for _bad in ["DROP", "DELETE", "INSERT", "UPDATE", "EXEC", "UNION", "ALTER", "--", ";",
                     "OR 1=1", "OR 1 =1", "OR TRUE", "' OR '", "\"OR\""]:
            if _bad in _where_upper:
                return "", []
        _first_col = _re.split(r'[\s(]', _where_upper.strip())[0]
        if _first_col and _first_col not in {c.upper() for c in _ALLOWED_COLS}:
            return "", []
        return _where, _params
    except Exception:
        return "", []


# ── 언어 단축 참조 (전체 앱에서 사용) ────────────────────────────────
T = _T[st.session_state.lang]

# ── 헤더 ─────────────────────────────────────────────────────────
st.markdown(f"""
<div class="hvdc-header">
    <span class="hvdc-header-icon">✉</span>
    <div>
        <div class="hvdc-header-title">HVDC Email Search</div>
        <div class="hvdc-header-caption">{T["caption"]}</div>
    </div>
    <div class="hvdc-header-badge">51,964 emails · DuckDB FTS</div>
</div>
""", unsafe_allow_html=True)

# ── DB 초기화 (atomic, top-level) ────────────────────────────────
if _DB_TMP.exists():
    _DB_TMP.unlink(missing_ok=True)

if not DB_LOCAL.exists():
    _download_error = None
    with st.status(T["db_init"], expanded=True) as _status:
        _bar = st.progress(0)
        try:
            with requests.get(DB_URL, stream=True, timeout=(30, 900)) as _r:
                _r.raise_for_status()
                _total = int(_r.headers.get("content-length", 0))
                _downloaded = 0
                with open(_DB_TMP, "wb") as _f:
                    for _chunk in _r.iter_content(chunk_size=256 * 1024):
                        _f.write(_chunk)
                        _downloaded += len(_chunk)
                        if _total:
                            _pct = min(int(_downloaded / _total * 100), 100)
                            _bar.progress(_pct, text=f"{_downloaded//1024//1024} MB / {_total//1024//1024} MB")
            _DB_TMP.rename(DB_LOCAL)
            _status.update(label=f"✅ {T['db_ok']}", state="complete")
        except Exception as _exc:
            _DB_TMP.unlink(missing_ok=True)
            _download_error = str(_exc)
            _status.update(label=f"❌ {T['db_fail']}", state="error")
    if _download_error:
        st.error(T["db_err"] + _download_error)
        st.stop()
    else:
        st.rerun()

months, sites, stages = load_filter_options()

# ── 첨부파일 폴더 링크 ────────────────────────────────────────────
DRIVE_FOLDERS = [
    ("Attachment Folder 1 (Apr 2026 early)",  "https://drive.google.com/drive/folders/1nGE7Ldq8aC0ut8ZuiA8aCUa77f362DxK"),
    ("Attachment Folder 2 (Apr-May 2026)",    "https://drive.google.com/drive/folders/1FwcHBvKqy12CqHMPcEOp09y0J8stLZZ2"),
    ("Attachment Folder 3 (May 2026)",        "https://drive.google.com/drive/folders/1gmpdc7MUeWXv0T5mitUemF2EKzcCRSDH"),
    ("Attachment Folder 4 (Jun 2026 early)",  "https://drive.google.com/drive/folders/1Th_BvMreMVvGdfrQTzp5gUDpKi0f1I63"),
    ("Attachment Folder 5 (Jun 2026 latest)", "https://drive.google.com/drive/folders/1btH18NykL9wDKKuJZZBTSUGCsYkXcaxm"),
]

# ── 사이드바 ────────────────────────────────────────────────────────
with st.sidebar:
    # 언어 토글
    _lc1, _lc2 = st.columns(2)
    if _lc1.button(
        "KO",
        use_container_width=True,
        type="primary" if st.session_state.lang == "ko" else "secondary",
        key="btn_lang_ko",
    ):
        st.session_state.lang = "ko"
        st.rerun()
    if _lc2.button(
        "EN",
        use_container_width=True,
        type="primary" if st.session_state.lang == "en" else "secondary",
        key="btn_lang_en",
    ):
        st.session_state.lang = "en"
        st.rerun()

    st.divider()

    # 필터 섹션
    st.markdown(f'<div class="sidebar-label">{T["label_search_filter"]}</div>', unsafe_allow_html=True)

    query_text = st.text_input(
        T["kw_search"],
        placeholder=T["kw_placeholder"],
        help=T["kw_help"],
    )

    sel_months = st.multiselect("Month", months, help="202410 = Oct 2024")
    sel_sites  = st.multiselect("Site",  sites)
    sel_stages = st.multiselect("Stage", stages)

    with st.expander(T["adv_filter"]):
        sender_filter = st.text_input(T["sender_filter_label"], placeholder=T["sender_filter_ph"])
        case_filter   = st.text_input(T["case_filter_label"],   placeholder=T["case_filter_ph"])

    max_rows = st.slider(T["max_rows"], 50, 2000, 200, 50)
    use_query_rewrite = st.checkbox(T["query_rewrite"], value=True)

    st.divider()

    # 첨부파일 폴더 섹션
    st.markdown(f'<div class="sidebar-label">{T["label_pdf_folders"]}</div>', unsafe_allow_html=True)
    for _label, _url in DRIVE_FOLDERS:
        st.markdown(f"[{_label}]({_url})")

    st.divider()
    with st.expander(T["db_diag"], expanded=False):
        if DB_LOCAL.exists():
            _size_mb = DB_LOCAL.stat().st_size // 1024 // 1024
            st.code(f"Path: {DB_LOCAL}\nSize: {_size_mb} MB\nExists: ✓", language="text")
            try:
                _emb_df = run_query("SELECT COUNT(*) FROM emails WHERE embedding IS NOT NULL")
                _emb_n = int(_emb_df.iloc[0, 0]) if not _emb_df.empty else 0
                st.code(f"Embeddings: {_emb_n:,} / 51,964", language="text")
            except Exception as _e:
                st.code(f"Embedding check failed:\n{_e}", language="text")
        else:
            st.code(f"Path: {DB_LOCAL}\nNot found ✗", language="text")

    _confirm_reset = st.checkbox(T["confirm_reset"])
    if st.button(T["btn_reset"], use_container_width=True, disabled=not _confirm_reset):
        st.cache_data.clear()
        st.cache_resource.clear()
        DB_LOCAL.unlink(missing_ok=True)
        _DB_TMP.unlink(missing_ok=True)
        st.rerun()


# ── 탭 (3개) ─────────────────────────────────────────────────────
tab_search, tab_analytics, tab_semantic = st.tabs([
    T["tab_search"],
    T["tab_analytics"],
    T["tab_semantic"],
])


# ════════════════════════════════════════════════════════════════
# TAB 1 — 검색 + AI 요약 + Case 스레드
# ════════════════════════════════════════════════════════════════
with tab_search:

    BASE_COLS_SHOW = [
        "no", "month", "subject", "sendername", "senderemail",
        "company_name", "recipientto", "deliverytime",
        "site", "stage", "hvdc_cases", "primary_case", "linkkey",
    ]
    SEARCH_HELPER_COLS = ["case_numbers", "lpo_numbers", "rowkey"]
    _available_cols = set(email_columns())
    COLS_SHOW = BASE_COLS_SHOW + [c for c in SEARCH_HELPER_COLS if c in _available_cols]

    WHERE: list[str] = []
    PARAMS: list = []

    google_api_key = st.secrets.get("google_api_key", "")
    query_entities = _extract_entities(query_text)
    bm25_query   = query_text
    ko_raw_query = ""        # Korean input flag → recency ordering
    ko_en_terms  = []        # glossary English domain terms used (for badge)
    search_mode  = ""        # status badge: glossary / ilike / bm25 / rewrite
    q_clause     = ""        # query WHERE clause (kept separate from filters for fallback)
    q_params: list = []      # params bound to q_clause
    if query_text and _is_korean(query_text):
        # Korean: glossary-driven bilingual search (no Gemini literal translation).
        # all-MiniLM is English-only & literal "기성→established" hits company names,
        # so we match Korean variants by ILIKE and add PRECISE English domain BM25.
        ko_variants, ko_en_terms = _glossary_expand(query_text)
        ko_raw_query = query_text
        ilike_clauses = []
        ko_ilike_params: list = []
        for v in ko_variants:
            ilike_clauses.append("(subject ILIKE ? OR plaintextbody ILIKE ?)")
            ko_ilike_params.extend([f"%{v}%", f"%{v}%"])
        ko_ilike_expr = " OR ".join(ilike_clauses)   # Korean-variant match (no BM25)
        q_params.extend(ko_ilike_params)
        ko_where = ko_ilike_expr
        if ko_en_terms:
            en_join = " OR ".join(ko_en_terms)
            ko_where = f"({ko_where}) OR fts_main_emails.match_bm25(no, ?) IS NOT NULL"
            q_params.append(en_join)
            bm25_query  = en_join          # caption/badge shows domain terms used
            search_mode = "glossary"
        else:
            search_mode = "ilike"
        q_clause = f"({ko_where})"
    else:
        # English (or empty): optional synonym rewrite, then BM25
        if bm25_query and use_query_rewrite:
            with st.spinner(T["sem_translate"]):
                bm25_query = _rewrite_query(bm25_query, google_api_key)
                if bm25_query != query_text:
                    search_mode = "rewrite"
        if bm25_query:
            q_clause = "fts_main_emails.match_bm25(no, ?) IS NOT NULL"
            q_params.append(bm25_query)
            if not search_mode:
                search_mode = "bm25"

    if sel_months:
        ph = ", ".join(["?"] * len(sel_months))
        WHERE.append(f'"month" IN ({ph})')
        PARAMS.extend(sel_months)

    if sel_sites:
        ph = ", ".join(["?"] * len(sel_sites))
        WHERE.append(f'"site" IN ({ph})')
        PARAMS.extend(sel_sites)

    if sel_stages:
        ph = ", ".join(["?"] * len(sel_stages))
        WHERE.append(f'"stage" IN ({ph})')
        PARAMS.extend(sel_stages)

    if sender_filter:
        WHERE.append('"senderemail" ILIKE ?')
        PARAMS.append(f"%{sender_filter}%")

    if case_filter:
        WHERE.append('"hvdc_cases" ILIKE ?')
        PARAMS.append(f"%{case_filter}%")

    col_list = ", ".join(f'"{c}"' for c in COLS_SHOW)

    def _run_search(qc: str, qp: list, *, bm25_order_term: str = "",
                    select_extra: str = "", select_params: list | None = None,
                    order_by: str = ""):
        """Compose query-clause + filters and run. Returns (df, count, where_clause)."""
        select_params = select_params or []
        where_parts = ([qc] if qc else []) + WHERE
        wc = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""
        if order_by:
            sc, ob, ep = select_extra, order_by, select_params
        elif bm25_order_term:
            sc = ", fts_main_emails.match_bm25(no, ?) AS bm25_score"
            ob = "ORDER BY bm25_score DESC"
            ep = [bm25_order_term]
        else:
            sc = ""
            ob = 'ORDER BY "deliverytime" DESC'
            ep = []
        sql = f"SELECT {col_list}{sc} FROM emails {wc} {ob} LIMIT ?"
        params = ep + qp + PARAMS + [max_rows]
        cnt = count_emails(wc, tuple(qp + PARAMS))
        d = run_query(sql, params if params else None)
        return d, cnt, wc

    def _run_exact_search(query: str):
        terms = _identifier_terms(query)
        if not terms:
            return pd.DataFrame(), 0, ""

        preferred_text_cols = [
            "hvdc_cases", "primary_case", "case_numbers", "lpo_numbers",
            "subject", "senderemail", "company_name", "linkkey", "rowkey",
            "plaintextbody",
        ]
        text_cols = [col for col in preferred_text_cols if col in _available_cols]
        term_clauses = []
        term_params: list = []
        for term in terms:
            clean = _clean_id_value(term)
            field_parts = [_id_lookup_where('"no"')]
            term_params.extend(_id_lookup_params(clean))
            is_short_numeric = clean.isdigit() and len(clean) <= 5
            is_date_like = clean.isdigit() and (
                len(clean) == 4 and clean.startswith("20")
                or len(clean) == 6 and clean.startswith("20")
            )
            allowed_cols = [] if is_short_numeric or is_date_like else text_cols
            for col in allowed_cols:
                field_parts.append(f'CAST("{col}" AS VARCHAR) ILIKE ?')
                term_params.append(f"%{term}%")
            term_clauses.append("(" + " OR ".join(field_parts) + ")")

        where_parts = ["(" + " OR ".join(term_clauses) + ")"] + WHERE
        wc = "WHERE " + " AND ".join(where_parts)
        sql = f'SELECT {col_list} FROM emails {wc} ORDER BY "deliverytime" DESC LIMIT ?'
        params = term_params + PARAMS + [max_rows]
        d = run_query(sql, params)
        cnt = count_emails(wc, tuple(term_params + PARAMS))
        if d.empty:
            return d, cnt, wc

        d = d.copy()
        d["exact_tier"] = d.apply(lambda row: _exact_match_tier(row, terms), axis=1)
        d["_exact_delivery"] = pd.to_datetime(d.get("deliverytime"), errors="coerce")
        d = d.sort_values(
            ["exact_tier", "_exact_delivery"],
            ascending=[True, False],
            na_position="last",
        ).drop(columns=["_exact_delivery"], errors="ignore")
        d["exact_rank"] = range(1, len(d) + 1)
        d["exact_score"] = 1.0
        d["match_reason"] = d.apply(
            lambda row: "exact identifier"
            + (f", {_field_hit_reason(row, query)}" if _field_hit_reason(row, query) else ", body"),
            axis=1,
        )
        return d, cnt, wc

    def _merge_search_results(primary: pd.DataFrame, exact: pd.DataFrame) -> pd.DataFrame:
        if exact.empty:
            return primary
        if primary.empty:
            return exact.drop(columns=["_dedupe_no"], errors="ignore")

        primary = primary.copy()
        exact = exact.copy()
        primary["_dedupe_no"] = primary["no"].apply(_clean_id_value)
        exact["_dedupe_no"] = exact["no"].apply(_clean_id_value)
        exact_by_no = exact.drop_duplicates("_dedupe_no", keep="first").set_index("_dedupe_no")

        for col in ["exact_rank", "exact_score", "exact_tier", "match_reason"]:
            if col not in exact_by_no.columns:
                continue
            mapped = primary["_dedupe_no"].map(exact_by_no[col])
            if col in primary.columns:
                primary[col] = mapped.combine_first(primary[col])
            else:
                primary[col] = mapped

        exact_only = exact[~exact["_dedupe_no"].isin(set(primary["_dedupe_no"]))]
        merged = pd.concat([primary, exact_only], ignore_index=True, sort=False)
        return merged.drop(columns=["_dedupe_no"], errors="ignore")

    # Stage 1 — primary search
    with st.spinner(T["searching"]):
        if search_mode == "glossary":
            # Korean-variant exact matches rank first (tier 0), English domain BM25
            # matches below (tier 1); recency within each tier. Preserves precision.
            _tier = f", CASE WHEN ({ko_ilike_expr}) THEN 0 ELSE 1 END AS ko_tier"
            _sel_params = list(ko_ilike_params)
            if ko_en_terms:
                _tier += ", fts_main_emails.match_bm25(no, ?) AS bm25_score"
                _sel_params.append(bm25_query)
            df, total_cnt, where_clause = _run_search(
                q_clause, q_params,
                select_extra=_tier, select_params=_sel_params,
                order_by='ORDER BY ko_tier ASC, "deliverytime" DESC',
            )
        else:
            _bm25_order = bm25_query if (bm25_query and not ko_raw_query) else ""
            df, total_cnt, where_clause = _run_search(
                q_clause, q_params, bm25_order_term=_bm25_order)

    exact_df = pd.DataFrame()
    exact_cnt = 0
    if query_text and _is_identifier_query(query_text):
        exact_df, exact_cnt, exact_where_clause = _run_exact_search(query_text)
        if not exact_df.empty:
            df = _merge_search_results(df, exact_df)
            total_cnt = max(total_cnt, exact_cnt)
            if not q_clause:
                where_clause = exact_where_clause
                search_mode = "exact"

    # Phase C — zero-result fallback chain (pure SQL, no API). Escalate only on empty.
    if df.empty and query_text:
        import re as _re_fb
        _tokens = [t for t in _re_fb.split(r"\s+", query_text.strip()) if len(t) >= 3]
        # Stage 2 — English multi-token BM25 OR (recall for AND-strict multi-word queries)
        if not ko_raw_query and len(_tokens) >= 2:
            _or = " OR ".join(_tokens[:4])
            _d, _c, _wc = _run_search(
                "fts_main_emails.match_bm25(no, ?) IS NOT NULL", [_or],
                bm25_order_term=_or,
            )
            if not _d.empty:
                df, total_cnt, where_clause, search_mode, bm25_query = _d, _c, _wc, "token", _or
        # Stage 3 — broad ILIKE substring (subject + body) on each token
        if df.empty:
            _toks = _tokens or ([ko_raw_query] if ko_raw_query else [query_text])
            _cl, _pa = [], []
            for t in _toks[:4]:
                _cl.append("(subject ILIKE ? OR plaintextbody ILIKE ?)")
                _pa.extend([f"%{t}%", f"%{t}%"])
            _d, _c, _wc = _run_search("(" + " OR ".join(_cl) + ")", _pa)
            if not _d.empty:
                df, total_cnt, where_clause, search_mode = _d, _c, _wc, "ilike_fb"

    if not df.empty and query_text:
        df = _search_copilot_rerank(df, bm25_query or query_text, query_entities)

    c1, c2, c3 = st.columns(3)
    c1.metric(T["metric_match"], f"{total_cnt:,}", help=T["metric_match_help"])
    c2.metric(T["metric_shown"], f"{len(df):,}",   help=f"{T['metric_shown_help']} {max_rows:,}")
    c3.metric(T["metric_total"], f"{get_total_emails():,}", help=T["metric_total_help"])

    st.divider()
    if search_mode == "glossary":
        st.caption(f"🎯 도메인 검색: `{ko_raw_query}` (한글 정확매칭 우선) + 영어 `{' OR '.join(ko_en_terms)}` 회수")
    elif search_mode == "ilike":
        st.caption(f"🔍 한글 검색: `{ko_raw_query}` (최신순 정렬)")
    elif search_mode == "rewrite":
        st.caption(f"🔍 확장 검색: `{bm25_query}`")
    elif search_mode == "token":
        st.caption(f"🧩 토큰 분리 검색(폴백): `{bm25_query}`")
    elif search_mode == "ilike_fb":
        st.caption(f"⚠ 부분 일치(폴백): `{query_text}` substring")
    elif search_mode == "exact":
        st.caption(f"🎯 정확 식별자 검색: `{query_text}`")
    if query_text and not exact_df.empty:
        st.caption(f"🎯 정확 식별자 보강: {len(exact_df):,}건을 상위 랭킹에 반영")
    if query_entities:
        st.caption(f"{T['detected_entities']}: {_entity_chip_text(query_entities)}")

    if df.empty:
        any_filter = bool(query_text or sel_months or sel_sites or sel_stages
                          or sender_filter or case_filter)
        if any_filter:
            st.info(T["no_results_filter"])
        else:
            st.info(T["no_results_empty"])
    else:
        df_show = df.copy()
        df_show = df_show.drop(columns=["ko_tier"], errors="ignore")  # internal sort key
        if query_text and not df_show.empty:
            _nos = [str(n) for n in df_show["no"].tolist()]
            _ph = ", ".join(["?"] * len(_nos))
            _body_batch = run_query(
                f"SELECT no, plaintextbody FROM emails WHERE no IN ({_ph})",
                _nos,
            )
            _bmap = (
                dict(zip(_body_batch["no"].astype(str), _body_batch["plaintextbody"]))
                if not _body_batch.empty else {}
            )
            _snippet_query = " ".join(dict.fromkeys([query_text, bm25_query]))
            df_show["snippet"] = df_show["no"].apply(
                lambda n: _extract_snippet(_bmap.get(str(n), ""), _snippet_query) or T["snip_none"]
            )
            df_show["entities"] = df_show.apply(
                lambda row: _entity_chip_text(_merge_entities(
                    query_entities,
                    _extract_entities(
                        " ".join(
                            str(row.get(col, "") or "")
                            for col in ["subject", "sendername", "company_name", "site", "stage", "hvdc_cases"]
                        )
                        + " "
                        + str(_bmap.get(str(row.get("no")), "") or "")
                    ),
                )),
                axis=1,
            )
        pdf_quick_items = []
        if "linkkey" in df_show.columns:
            for _, _row in df_show.head(20).iterrows():
                _linkkey = _row.get("linkkey", "")
                _parts = _pdf_parts(_linkkey)
                if not _parts:
                    continue
                _subject = str(_row.get("subject", "") or "").strip()
                if len(_subject) > 80:
                    _subject = _subject[:77] + "..."
                pdf_quick_items.append({
                    "no": _clean_id_value(_row.get("no", "")),
                    "subject": _subject,
                    "view_parts": _parts,
                    "download_parts": _pdf_download_parts(_linkkey),
                })
            df_show["pdf_link"] = (
                df_show["linkkey"].apply(_pdf_url).replace("", None)
            )
            df_show["pdf_download_link"] = (
                df_show["linkkey"].apply(_pdf_download_url).replace("", None)
            )
            df_show = df_show.drop(columns=["linkkey"])
        else:
            df_show["pdf_link"] = None
            df_show["pdf_download_link"] = None

        _snippets = {}
        if "snippet" in df_show.columns:
            _snippets = dict(zip(df_show["no"].astype(str), df_show["snippet"]))
            df_table = df_show.drop(columns=["snippet"])
        else:
            df_table = df_show
        df_table = df_table.drop(
            columns=[
                "bm25_norm", "vector_norm", "entity_match", "recency_score",
                "decision_signal", "field_match", "exact_rank", "exact_score",
                "exact_tier", *SEARCH_HELPER_COLS,
            ],
            errors="ignore",
        )
        df_table = _clean_id_columns(df_table)

        st.dataframe(
            df_table,
            use_container_width=True,
            column_config={
                "no":           st.column_config.TextColumn("no", width=70),
                "month":        st.column_config.TextColumn("month", width=90),
                "subject":      st.column_config.TextColumn(T["col_subject"],  width=280),
                "senderemail":  st.column_config.TextColumn(T["col_sender"],   width=180),
                "deliverytime": st.column_config.TextColumn(T["col_received"], width=140),
                "hvdc_cases":   st.column_config.TextColumn(T["col_cases"],    width=170),
                "bm25_score":   st.column_config.NumberColumn(T["col_score"],  format="%.3f"),
                "search_copilot_score": st.column_config.NumberColumn(T["col_score"], format="%.3f"),
                "entities":     st.column_config.TextColumn(T["col_entities"], width=260),
                "match_reason": st.column_config.TextColumn(T["col_match_reason"], width=220),
                "pdf_link":     st.column_config.LinkColumn(T["col_pdf"],      display_text="Open", width=70),
                "pdf_download_link": st.column_config.LinkColumn(T["btn_pdf_download"], display_text="Download", width=110),
            },
            hide_index=True,
            height=500,
        )

        if pdf_quick_items:
            with st.expander(T["pdf_quick_links"], expanded=False):
                for _item in pdf_quick_items:
                    st.caption(f"#{_item['no']} - {_item['subject']}")
                    for _i, (_view_part, _download_part) in enumerate(
                        zip(_item["view_parts"], _item["download_parts"]),
                        1,
                    ):
                        _view_label, _view_url = _view_part
                        _, _download_url = _download_part
                        _view_button = _view_label if len(_item["view_parts"]) > 1 else T["btn_pdf"]
                        _download_button = (
                            f"{T['btn_pdf_download']} {_i}"
                            if len(_item["download_parts"]) > 1
                            else T["btn_pdf_download"]
                        )
                        _view_col, _download_col = st.columns(2)
                        _view_col.link_button(
                            _view_button,
                            _view_url,
                            type="primary",
                            width="stretch",
                        )
                        _download_col.link_button(
                            _download_button,
                            _download_url,
                            width="stretch",
                        )
                    st.divider()

        _refine_text = st.text_input(
            T["refine_placeholder"],
            key="refine_input",
            placeholder="예: 2025, DSV, MOSB",
        )
        if _refine_text and not df_show.empty:
            _cols = ["subject", "sendername", "senderemail", "deliverytime",
                     "company_name", "hvdc_cases", "month"]
            _mask = pd.Series([False] * len(df_show), index=df_show.index)
            for _col in _cols:
                if _col in df_show.columns:
                    _mask |= df_show[_col].astype(str).str.contains(
                        _refine_text, case=False, na=False
                    )
            _df_refined = df_show[_mask]
            st.caption(f"🔍 **'{_refine_text}'** — {len(_df_refined)}건")
            if not _df_refined.empty:
                _df_ref_table = _df_refined.drop(
                    columns=[
                        c for c in [
                            "snippet", "pdf_link", "pdf_download_link", "bm25_norm", "vector_norm",
                            "entity_match", "recency_score", "decision_signal", "field_match",
                            "exact_rank", "exact_score", "exact_tier", *SEARCH_HELPER_COLS,
                        ]
                        if c in _df_refined.columns
                    ]
                )
                _df_ref_table = _clean_id_columns(_df_ref_table)
                st.dataframe(
                    _df_ref_table,
                    use_container_width=True,
                    column_config={
                        "no":           st.column_config.TextColumn("no", width=70),
                        "month":        st.column_config.TextColumn("month", width=90),
                        "subject":      st.column_config.TextColumn(T["col_subject"],  width=280),
                        "senderemail":  st.column_config.TextColumn(T["col_sender"],   width=180),
                        "deliverytime": st.column_config.TextColumn(T["col_received"], width=140),
                        "match_reason": st.column_config.TextColumn(T["col_match_reason"], width=220),
                    },
                    hide_index=True,
                    height=300,
                )

        if _snippets:
            with st.expander(T["snip_header"], expanded=True):
                for _, row in df_show.head(20).iterrows():
                    snip = _snippets.get(str(row["no"]), "")
                    if snip and snip != T["snip_none"]:
                        subj = str(row.get("subject", ""))[:60]
                        st.caption(f"**#{row['no']}** — {subj}")
                        st.markdown(snip)
                        st.markdown("---")

        if google_api_key and not df_show.empty:
            if st.button(T["btn_bulk_summary"], key="bulk_summary"):
                with st.spinner(T["bulk_summary_spinner"]):
                    _rows = df_show.head(10)
                    _lines = [
                        f"{i+1}. [{r['subject']}] {r.get('snippet', r.get('sendername', ''))}"
                        for i, (_, r) in enumerate(_rows.iterrows())
                    ]
                    _prompt = (
                        f"다음 HVDC 프로젝트 이메일 {len(_lines)}건의 핵심 내용을 한국어로 3줄로 요약하세요. "
                        f"공통 주제, 주요 이슈, 액션 아이템을 중심으로:\n\n" + "\n".join(_lines)
                    )
                    try:
                        from google import genai as _genai
                        _client = _genai.Client(api_key=google_api_key)
                        _resp = _client.models.generate_content(model="gemini-2.5-flash", contents=_prompt)
                        st.subheader(T["bulk_summary_header"])
                        st.info(_resp.text)
                    except Exception as _e:
                        st.warning(f"Gemini 오류: {_e}")

        # ── P3-1: Issue Clustering  ──────────────────────────────────
        if not df_show.empty:
            st.divider()
            _col_cl, _col_kd = st.columns(2)
            with _col_cl:
                if st.button(T["btn_cluster"], key="p3_cluster", use_container_width=True):
                    _clustered = _cluster_emails(df_show)
                    _dist = _clustered["issue_type"].value_counts().reset_index()
                    _dist.columns = ["이슈", "건수"]
                    st.subheader(T["cluster_header"])
                    st.dataframe(_dist, hide_index=True, use_container_width=True)
                    st.bar_chart(_dist.set_index("이슈")["건수"])

            # ── P3-2: Key Decision Finder ────────────────────────────
            with _col_kd:
                if st.button(T["btn_key_decisions"], key="p3_key_decisions", use_container_width=True):
                    with st.spinner("조회 중..."):
                        _kd_df = _key_decisions_query()
                    st.subheader(T["key_decisions_header"])
                    if not _kd_df.empty:
                        st.dataframe(
                            _kd_df,
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "subject":      st.column_config.TextColumn(T["col_subject"],  width=260),
                                "sendername":   st.column_config.TextColumn("Sender",          width=130),
                                "deliverytime": st.column_config.TextColumn(T["col_received"], width=120),
                                "hvdc_cases":   st.column_config.TextColumn(T["col_cases"],    width=140),
                            },
                        )
                    else:
                        st.info("결과 없음")

        # ── P3-3: Natural Language Query ─────────────────────────────
        if google_api_key:
            _nl_text = st.text_input(
                T["nl_query_placeholder"],
                key="nl_query_input",
                placeholder="예: 2025년 3월에 Mammoet가 보낸 MRR 관련 이메일",
            )
            st.caption(T["nl_query_caption"])
            if _nl_text:
                with st.spinner("Gemini SQL 변환 중..."):
                    _nl_where, _nl_params = _nl_to_sql(_nl_text, google_api_key)
                if _nl_where:
                    _nl_sql = (
                        f"SELECT no, deliverytime, subject, sendername, company_name, hvdc_cases "
                        f"FROM emails WHERE {_nl_where} ORDER BY deliverytime DESC LIMIT 50"
                    )
                    try:
                        _nl_result = run_query(_nl_sql, _nl_params if _nl_params else None)
                        st.subheader(T["nl_query_header"])
                        st.caption(f"WHERE `{_nl_where}`")
                        if not _nl_result.empty:
                            st.dataframe(
                                _nl_result,
                                use_container_width=True,
                                hide_index=True,
                                column_config={
                                    "subject":      st.column_config.TextColumn(T["col_subject"],  width=280),
                                    "sendername":   st.column_config.TextColumn("Sender",          width=140),
                                    "deliverytime": st.column_config.TextColumn(T["col_received"], width=120),
                                },
                            )
                        else:
                            st.info("조건에 맞는 이메일이 없습니다.")
                    except Exception as _nl_e:
                        st.warning(f"쿼리 오류: {_nl_e}")
                else:
                    st.info("Gemini가 조건을 인식하지 못했습니다. 더 구체적으로 입력해 주세요.")

        st.subheader(T["email_detail"])
        detail_subjects = {}
        for _, _detail_row in df.head(50).iterrows():
            _detail_no = _clean_id_value(_detail_row.get("no", ""))
            if not _detail_no or _detail_no in detail_subjects:
                continue
            detail_subjects[_detail_no] = str(_detail_row.get("subject", "") or "")
        row_no = st.selectbox(
            T["select_email"],
            options=list(detail_subjects),
            format_func=lambda x: (
                f"#{x}  "
                + detail_subjects.get(x, "")[:60]
            ),
        )
        if row_no:
            row_no_key = _clean_id_value(row_no)
            body_df = run_query(
                "SELECT subject, sendername, senderemail, deliverytime, "
                "recipientto, plaintextbody, linkkey, primary_case "
                f"FROM emails WHERE {_id_lookup_where('no')}",
                _id_lookup_params(row_no_key),
            )
            if not body_df.empty:
                r = body_df.iloc[0]
                col_a, col_b = st.columns(2)
                col_a.markdown(f"**{T['col_subject']}**  \n{r['subject']}")
                col_a.markdown(f"**{T['col_sender']}**  \n{r['sendername']}  \n`{r['senderemail']}`")
                col_b.markdown(f"**{T['col_received']}**  \n{r['deliverytime']}")
                col_b.markdown(f"**{T['col_recipients']}**  \n{r['recipientto']}")

                _body_text = str(r["plaintextbody"] or "")
                lk = r.get("linkkey") if hasattr(r, "get") else r["linkkey"]
                pdf_parts = _pdf_parts_for_email(lk, r.get("subject", ""), _body_text)
                if pdf_parts:
                    pdf_download_parts = _pdf_download_parts_for_email(lk, r.get("subject", ""), _body_text)
                    _label_multi = len(pdf_parts) > 1
                    for _i, ((_plabel, _purl), (_, _durl)) in enumerate(
                        zip(pdf_parts, pdf_download_parts),
                        1,
                    ):
                        _view_col, _download_col = st.columns(2)
                        _view_col.link_button(
                            _plabel if _label_multi else T["btn_pdf"],
                            _purl,
                            type="primary",
                            width="stretch",
                        )
                        _download_col.link_button(
                            f"{T['btn_pdf_download']} {_i}" if _label_multi else T["btn_pdf_download"],
                            _durl,
                            width="stretch",
                        )
                else:
                    st.markdown(f"**{T['pdf_folder_alt']}**")
                    for _label, _url in DRIVE_FOLDERS:
                        st.markdown(f"- [{_label}]({_url})")

                st.text_area(T["col_body"], value=_body_text or f"({T['col_body']} N/A)", height=380)

                _entities = _extract_entities(_body_text)
                if _entities:
                    st.markdown("**Entities:**")
                    for _tag, _vals in _entities.items():
                        st.markdown("`" + _tag + "` " + " ".join(f"`{v}`" for v in _vals))

                if google_api_key:
                    if st.button(T["btn_ai"], key=f"gemini_{row_no}"):
                        with st.spinner(T["ai_spinner"]):
                            summary = summarize_with_gemini(
                                str(r["subject"] or ""),
                                str(r["plaintextbody"] or ""),
                                google_api_key,
                            )
                        import html as _html
                        st.markdown(
                            f'<div class="ai-summary-card">{_html.escape(summary)}</div>',
                            unsafe_allow_html=True,
                        )
                else:
                    st.caption(T["ai_no_key"])

                if has_embeddings():
                    with st.expander(T["sim_header"]):
                        _emb_row = run_query(
                            f"SELECT embedding FROM emails WHERE {_id_lookup_where('no')}",
                            _id_lookup_params(row_no_key),
                        )
                        if _emb_row.empty or _emb_row.iloc[0, 0] is None:
                            st.caption(T["sim_no_emb"])
                        else:
                            with st.spinner(T["sim_searching"]):
                                _evec = _emb_row.iloc[0, 0]
                                if hasattr(_evec, "tolist"):
                                    _evec = _evec.tolist()
                                _sim_df = run_query(
                                    "SELECT no, subject, sendername, deliverytime, company_name, "
                                    "array_cosine_similarity(embedding, ?::FLOAT[384]) AS sim_score "
                                    f"FROM emails WHERE NOT {_id_lookup_where('no')} AND embedding IS NOT NULL "
                                    "ORDER BY sim_score DESC LIMIT 5",
                                    [_evec] + _id_lookup_params(row_no_key),
                                )
                            if not _sim_df.empty:
                                st.dataframe(
                                    _sim_df,
                                    use_container_width=True,
                                    hide_index=True,
                                    column_config={
                                        "subject":      st.column_config.TextColumn(T["col_subject"],  width=260),
                                        "sendername":   st.column_config.TextColumn(T["col_sender"],   width=140),
                                        "deliverytime": st.column_config.TextColumn(T["col_received"], width=140),
                                        "company_name": st.column_config.TextColumn(T["col_company"],  width=130),
                                        "sim_score":    st.column_config.NumberColumn(T["col_sim_score"], format="%.4f"),
                                    },
                                )

                primary_case_val = r.get("primary_case") if hasattr(r, "get") else r["primary_case"]
                if primary_case_val and str(primary_case_val).strip() not in ("", "None", "nan"):
                    with st.expander(f"{T['case_thread']}: {primary_case_val}"):
                        thread_df = run_query(
                            "SELECT no, deliverytime, subject, sendername FROM emails "
                            "WHERE primary_case = ? ORDER BY deliverytime",
                            [str(primary_case_val)],
                        )
                        if not thread_df.empty:
                            st.caption(f"{T['case_thread_count']} **{len(thread_df)}**")
                            fig_thread = px.scatter(
                                thread_df,
                                x="deliverytime",
                                y="sendername",
                                hover_data=["subject", "no"],
                                title=f"{T['thread_timeline']} — {primary_case_val}",
                                color="sendername",
                            )
                            fig_thread.update_layout(**_CHART, height=300)
                            fig_thread.update_traces(marker=dict(size=10))
                            st.plotly_chart(fig_thread, use_container_width=True)
                            st.dataframe(
                                thread_df[["no", "deliverytime", "sendername", "subject"]],
                                use_container_width=True,
                                hide_index=True,
                                height=200,
                                column_config={
                                    "subject": st.column_config.TextColumn(T["col_subject"], width=300),
                                },
                            )

                _sender_email_val = r.get("senderemail") if hasattr(r, "get") else r["senderemail"]
                _sender_name_val = r.get("sendername", "") if hasattr(r, "get") else str(r["sendername"])
                if _sender_email_val and str(_sender_email_val).strip() not in ("", "None", "nan"):
                    with st.expander(f"{T['btn_sender_history']}: {_sender_name_val}"):
                        _sender_df = run_query(
                            "SELECT no, deliverytime, subject, hvdc_cases FROM emails "
                            f"WHERE senderemail = ? AND NOT {_id_lookup_where('no')} "
                            "ORDER BY deliverytime DESC LIMIT 20",
                            [str(_sender_email_val)] + _id_lookup_params(row_no_key),
                        )
                        if not _sender_df.empty:
                            st.caption(f"**{len(_sender_df)}건**")
                            st.dataframe(
                                _sender_df,
                                use_container_width=True,
                                hide_index=True,
                                height=250,
                                column_config={
                                    "subject": st.column_config.TextColumn(T["col_subject"], width=300),
                                    "hvdc_cases": st.column_config.TextColumn(T["col_cases"], width=150),
                                },
                            )
            else:
                st.warning(T["detail_not_found"])

        st.divider()
        st.download_button(
            T["csv_download"],
            data=_clean_id_columns(df).to_csv(index=False).encode("utf-8-sig"),
            file_name="hvdc_email_search_result.csv",
            mime="text/csv",
        )


# ════════════════════════════════════════════════════════════════
# TAB 2 — 분석 (Feature 4: 네트워크 그래프)
# ════════════════════════════════════════════════════════════════
with tab_analytics:

    @st.cache_data(ttl=3600)
    def load_monthly_volume():
        df = run_query("""
            SELECT month, COUNT(*) AS email_count
            FROM emails
            WHERE month IS NOT NULL AND TRIM(month) != '' AND month != 'None'
            GROUP BY month
            ORDER BY month
        """)
        if not df.empty:
            df["month"] = _clean_month(df["month"])
            df = df.sort_values("month").reset_index(drop=True)
        return df

    @st.cache_data(ttl=3600)
    def load_top_senders(n: int = 20):
        return run_query(f"""
            SELECT
                COALESCE(
                    NULLIF(TRIM(company_name), ''),
                    NULLIF(TRIM(SPLIT_PART(senderemail, '@', 2)), ''),
                    'Unclassified'
                ) AS sender_group,
                COUNT(*) AS email_count
            FROM emails
            WHERE senderemail IS NOT NULL OR company_name IS NOT NULL
            GROUP BY sender_group
            ORDER BY email_count DESC
            LIMIT {n}
        """)

    @st.cache_data(ttl=3600)
    def load_site_stage_distribution():
        site_df = run_query("""
            SELECT
                COALESCE(NULLIF(TRIM(site), ''), 'Unclassified') AS site,
                COUNT(*) AS email_count
            FROM emails
            GROUP BY site
            ORDER BY email_count DESC
        """)
        stage_df = run_query("""
            SELECT
                COALESCE(NULLIF(TRIM(stage), ''), 'Unclassified') AS stage,
                COUNT(*) AS email_count
            FROM emails
            GROUP BY stage
            ORDER BY email_count DESC
        """)
        return site_df, stage_df

    def build_analytics_export(
        vol_df: pd.DataFrame,
        top_df: pd.DataFrame,
        site_df: pd.DataFrame,
        stage_df: pd.DataFrame,
    ) -> pd.DataFrame:
        frames = []
        if not vol_df.empty:
            frames.append(
                vol_df.rename(columns={"month": "dimension", "email_count": "count"})
                .assign(metric="monthly_volume")[["metric", "dimension", "count"]]
            )
        if not top_df.empty:
            frames.append(
                top_df.rename(columns={"sender_group": "dimension", "email_count": "count"})
                .assign(metric="top_sender")[["metric", "dimension", "count"]]
            )
        if not site_df.empty:
            frames.append(
                site_df.rename(columns={"site": "dimension", "email_count": "count"})
                .assign(metric="site_distribution")[["metric", "dimension", "count"]]
            )
        if not stage_df.empty:
            frames.append(
                stage_df.rename(columns={"stage": "dimension", "email_count": "count"})
                .assign(metric="stage_distribution")[["metric", "dimension", "count"]]
            )
        if not frames:
            return pd.DataFrame(columns=["metric", "dimension", "count"])
        return pd.concat(frames, ignore_index=True)

    @st.cache_data(ttl=3600)
    def load_heatmap():
        df = run_query("""
            SELECT
                month,
                COALESCE(site, 'Unknown') AS site,
                COUNT(*) AS email_count
            FROM emails
            WHERE month IS NOT NULL AND TRIM(month) != '' AND month != 'None'
            GROUP BY month, site
            ORDER BY month, site
        """)
        if not df.empty:
            df["month"] = _clean_month(df["month"])
        return df

    @st.cache_data(ttl=3600)
    def load_network_data():
        return run_query("""
            SELECT
                COALESCE(company_name, SPLIT_PART(senderemail, '@', 2)) AS source,
                COALESCE(
                    NULLIF(SPLIT_PART(SPLIT_PART(recipientto, '@', 2), '.', 1), ''),
                    'Unknown'
                ) AS target,
                COUNT(*) AS weight
            FROM emails
            WHERE company_name IS NOT NULL
              AND recipientto IS NOT NULL
              AND recipientto NOT LIKE '%None%'
            GROUP BY 1, 2
            HAVING COUNT(*) >= 5
            ORDER BY weight DESC
            LIMIT 150
        """)

    vol_df = load_monthly_volume()
    top_df = load_top_senders(20)
    heat_df = load_heatmap()
    site_df, stage_df = load_site_stage_distribution()
    analytics_export_df = build_analytics_export(vol_df, top_df, site_df, stage_df)

    total_volume = int(vol_df["email_count"].sum()) if not vol_df.empty else get_total_emails()
    peak_month = "-"
    peak_count = 0
    if not vol_df.empty:
        peak_row = vol_df.sort_values("email_count", ascending=False).iloc[0]
        peak_month = str(peak_row["month"])
        peak_count = int(peak_row["email_count"])

    metric_total, metric_peak, metric_sites, metric_stages = st.columns(4)
    metric_total.metric(T["metric_vol"],  f"{total_volume:,}")
    metric_peak.metric(T["metric_peak"],  peak_month, f"{peak_count:,}" if peak_count else None)
    metric_sites.metric("Site",  f"{len(site_df):,}")
    metric_stages.metric("Stage", f"{len(stage_df):,}")

    if not analytics_export_df.empty:
        st.download_button(
            T["analytics_csv"],
            data=analytics_export_df.to_csv(index=False).encode("utf-8-sig"),
            file_name="hvdc_email_analytics.csv",
            mime="text/csv",
        )

    sub_vol, sub_heat, sub_dist, sub_network = st.tabs([
        T["subtab_vol"],
        T["subtab_heat"],
        T["subtab_dist"],
        T["subtab_net"],
    ])

    with sub_vol:
        st.subheader(T["vol_title"])
        if vol_df.empty:
            st.info(T["vol_no_data"])
        else:
            fig_vol = px.bar(
                vol_df, x="month", y="email_count",
                labels={"month": T["axis_month"], "email_count": T["axis_email_count"]},
                color="email_count",
                color_continuous_scale=_SEQ,
            )
            fig_vol.update_layout(
                **_CHART,
                showlegend=False,
                coloraxis_showscale=False,
                height=340,
                xaxis=dict(title=T["axis_month"], tickangle=-45, type="category", tickfont=dict(size=11)),
                yaxis=dict(title=T["axis_email_count"], gridcolor="#E5E7EB"),
            )
            fig_vol.update_traces(hovertemplate=f"<b>%{{x}}</b><br>{T['axis_email_count']}: %{{y:,}}<extra></extra>")
            st.plotly_chart(fig_vol, use_container_width=True)

            _, col_top = st.columns([3, 2])
            with col_top:
                st.subheader(T["top_senders"])
                if not top_df.empty:
                    fig_top = px.bar(
                        top_df, x="email_count", y="sender_group",
                        orientation="h",
                        labels={"email_count": T["axis_email_count"], "sender_group": ""},
                        color="email_count",
                        color_continuous_scale=_SEQ,
                    )
                    fig_top.update_layout(
                        **_CHART,
                        showlegend=False,
                        coloraxis_showscale=False,
                        yaxis=dict(categoryorder="total ascending"),
                        xaxis=dict(title=T["axis_email_count"], gridcolor="#E5E7EB"),
                        height=400,
                    )
                    fig_top.update_traces(hovertemplate=f"<b>%{{y}}</b><br>{T['axis_email_count']}: %{{x:,}}<extra></extra>")
                    st.plotly_chart(fig_top, use_container_width=True)

            with st.expander(T["raw_data"]):
                st.dataframe(vol_df, use_container_width=True, hide_index=True)

    with sub_heat:
        st.subheader(T["heat_title"])
        if heat_df.empty:
            st.info(T["heat_no_data"])
        else:
            pivot = heat_df.pivot_table(
                index="site", columns="month",
                values="email_count", fill_value=0,
            )
            pivot.columns = [str(c) for c in pivot.columns]
            fig_heat = px.imshow(
                pivot,
                labels={"x": T["axis_month"], "y": T["axis_site"], "color": T["axis_email_count"]},
                color_continuous_scale=_SEQ,
                aspect="auto",
                text_auto=False,
            )
            fig_heat.update_layout(
                **_CHART,
                height=400,
                xaxis=dict(type="category", tickangle=-45, tickfont=dict(size=12)),
            )
            fig_heat.update_traces(hovertemplate=f"<b>%{{y}}</b> · %{{x}}<br>{T['axis_email_count']}: %{{z:,}}<extra></extra>")
            st.plotly_chart(fig_heat, use_container_width=True)

    with sub_dist:
        st.subheader(T["dist_title"])
        col_site, col_stage = st.columns(2)

        with col_site:
            if site_df.empty:
                st.info(T["site_no_data"])
            else:
                fig_site = px.pie(
                    site_df.head(12),
                    names="site",
                    values="email_count",
                    color_discrete_sequence=_PIE_COLORS,
                )
                fig_site.update_traces(
                    hole=0.45,
                    hovertemplate=f"<b>%{{label}}</b><br>{T['axis_email_count']}: %{{value:,}}<extra></extra>",
                )
                fig_site.update_layout(**_CHART, height=360, legend_title_text="Site")
                st.plotly_chart(fig_site, use_container_width=True)

        with col_stage:
            if stage_df.empty:
                st.info(T["stage_no_data"])
            else:
                fig_stage = px.pie(
                    stage_df.head(12),
                    names="stage",
                    values="email_count",
                    color_discrete_sequence=_PIE_COLORS,
                )
                fig_stage.update_traces(
                    hole=0.45,
                    hovertemplate=f"<b>%{{label}}</b><br>{T['axis_email_count']}: %{{value:,}}<extra></extra>",
                )
                fig_stage.update_layout(**_CHART, height=360, legend_title_text="Stage")
                st.plotly_chart(fig_stage, use_container_width=True)

        st.dataframe(
            analytics_export_df,
            use_container_width=True,
            hide_index=True,
            height=320,
            column_config={
                "metric":     st.column_config.TextColumn(T["col_metric"],    width=160),
                "dimension":  st.column_config.TextColumn(T["col_dim"],       width=220),
                "count":      st.column_config.NumberColumn(T["col_count"],   format="%d"),
            },
        )

    with sub_network:
        st.subheader(T["net_title"])
        st.caption(T["net_caption"])

        net_df = load_network_data()
        if net_df.empty:
            st.info(T["net_no_data"])
        else:
            try:
                import networkx as nx

                G = nx.from_pandas_edgelist(
                    net_df, source="source", target="target",
                    edge_attr="weight", create_using=nx.DiGraph()
                )

                @st.cache_data(show_spinner=False)
                def _compute_layout(_edge_list: list, _node_list: list) -> dict:
                    _G = nx.DiGraph()
                    _G.add_nodes_from(_node_list)
                    _G.add_edges_from(_edge_list)
                    return nx.spring_layout(_G, seed=42, k=2.0)

                pos = _compute_layout(list(G.edges()), list(G.nodes()))

                edge_traces = []
                for u, v, data in G.edges(data=True):
                    x0, y0 = pos.get(u, (0.0, 0.0))
                    x1, y1 = pos.get(v, (0.0, 0.0))
                    w = data.get("weight", 1)
                    edge_traces.append(go.Scatter(
                        x=[x0, x1, None], y=[y0, y1, None],
                        mode="lines",
                        line=dict(width=min(w / 20, 5), color="#5DADE2"),
                        hoverinfo="none",
                        showlegend=False,
                    ))

                node_x = [pos.get(n, (0.0, 0.0))[0] for n in G.nodes()]
                node_y = [pos.get(n, (0.0, 0.0))[1] for n in G.nodes()]
                node_text = list(G.nodes())
                node_size = [
                    max(10, min(40, G.degree(n) * 4)) for n in G.nodes()
                ]
                node_trace = go.Scatter(
                    x=node_x, y=node_y,
                    mode="markers+text",
                    text=node_text,
                    textposition="top center",
                    textfont=dict(size=12),
                    marker=dict(
                        size=node_size,
                        color=[G.degree(n) for n in G.nodes()],
                        colorscale=[[0, "#AED6F1"], [1, "#1F5276"]],
                        showscale=True,
                        colorbar=dict(title=T["connections"], thickness=12),
                        line=dict(width=1, color="#FFFFFF"),
                    ),
                    hovertemplate=f"<b>%{{text}}</b><br>{T['connections']}: %{{marker.size}}<extra></extra>",
                )

                fig_net = go.Figure(data=edge_traces + [node_trace])
                fig_net.update_layout(
                    **_CHART,
                    height=600,
                    showlegend=False,
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                )
                st.plotly_chart(fig_net, use_container_width=True)

            except ImportError:
                st.info(T["net_fallback"])
                top_net = net_df.sort_values("weight", ascending=False).head(30)
                top_net["link"] = top_net["source"] + " → " + top_net["target"]
                fig_fallback = px.bar(
                    top_net, x="weight", y="link", orientation="h",
                    labels={"weight": T["col_weight"], "link": ""},
                    color="weight", color_continuous_scale=_SEQ,
                )
                fig_fallback.update_layout(**_CHART, height=600,
                    yaxis=dict(categoryorder="total ascending"))
                st.plotly_chart(fig_fallback, use_container_width=True)

            st.dataframe(
                net_df.sort_values("weight", ascending=False).head(30),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "source": st.column_config.TextColumn(T["col_source"], width=200),
                    "target": st.column_config.TextColumn(T["col_target"], width=200),
                    "weight": st.column_config.NumberColumn(T["col_weight"], format="%d"),
                },
            )


# ════════════════════════════════════════════════════════════════
# TAB 3 — 시맨틱 검색 (Feature 2)
# ════════════════════════════════════════════════════════════════
with tab_semantic:
    st.subheader(T["sem_title"])

    _has_emb = has_embeddings()
    if not _has_emb:
        st.info(T["sem_no_emb"])
    else:
        google_api_key = st.secrets.get("google_api_key", "")
        sem_query = st.text_input(
            T["sem_query_label"],
            placeholder=T["sem_query_ph"],
            help=T["sem_query_help"],
        )
        sem_top_k = st.slider(T["sem_top_k"], 10, 100, 30, 10)
        use_hybrid = st.checkbox(T["sem_hybrid"], value=True)

        if sem_query and st.button(T["sem_run"]):
            # Multilingual model embeds Korean natively — no translation step.
            _embed_query = sem_query
            with st.spinner(T["sem_embedding"]):
                qvec = get_query_embedding(_embed_query)

            if qvec:
                with st.spinner(T["sem_searching"]):
                    vec_df = run_query(
                        f"SELECT no, subject, sendername, deliverytime, company_name, "
                        f"array_cosine_similarity(embedding, ?::FLOAT[384]) AS cosine_score "
                        f"FROM emails "
                        f"WHERE embedding IS NOT NULL "
                        f"ORDER BY cosine_score DESC LIMIT {sem_top_k * 2}",
                        [qvec],
                    )

                    if use_hybrid and sem_query:
                        hybrid_query = _rewrite_query(
                            sem_query,
                            google_api_key if use_query_rewrite else "",
                        )
                        bm25_df = run_query(
                            f"SELECT no, fts_main_emails.match_bm25(no, ?) AS bm25_score "
                            f"FROM emails ORDER BY bm25_score DESC LIMIT {sem_top_k * 2}",
                            [hybrid_query],
                        )
                        if not bm25_df.empty and not vec_df.empty:
                            bm25_max = float(bm25_df["bm25_score"].max() or 1)
                            bm25_df["bm25_norm"] = bm25_df["bm25_score"] / bm25_max
                            merged = vec_df.merge(bm25_df[["no", "bm25_norm"]], on="no", how="left").fillna(0)
                            result_df = _search_copilot_rerank(merged, hybrid_query).head(sem_top_k)
                            score_col_name = "search_copilot_score"
                        else:
                            result_df = vec_df.head(sem_top_k)
                            score_col_name = "cosine_score"
                    else:
                        result_df = vec_df.head(sem_top_k)
                        score_col_name = "cosine_score"

                    if len(result_df) == 0:
                        st.warning(T["sem_no_result"])
                    else:
                        st.success(f"{T['sem_done']} — {len(result_df)}")
                    result_display_df = result_df.drop(
                        columns=[
                            "bm25_norm", "vector_norm", "entity_match",
                            "recency_score", "decision_signal", "field_match",
                            "exact_rank", "exact_score", "match_reason",
                        ],
                        errors="ignore",
                    )
                    st.dataframe(
                        result_display_df,
                        use_container_width=True,
                        hide_index=True,
                        height=500,
                        column_config={
                            "subject":       st.column_config.TextColumn(T["col_subject"],   width=200),
                            "sendername":    st.column_config.TextColumn(T["col_sender"],    width=150),
                            "deliverytime":  st.column_config.TextColumn(T["col_received"],  width=140),
                            "company_name":  st.column_config.TextColumn(T["col_company"],   width=150),
                            score_col_name:  st.column_config.NumberColumn(T["col_similarity"], format="%.4f"),
                        },
                    )

"""
HVDC Email Search — Streamlit + DuckDB  v2.0
Features: BM25 Search | Gemini AI Summary | Case Thread | Network Graph | Semantic Search
"""
import requests
import duckdb
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

# ── DB 설정 ─────────────────────────────────────────────────────────
DB_URL   = "https://github.com/macho715/sct_email/releases/download/v2.0/hvdc_mail.duckdb"
DB_LOCAL = Path("/tmp/hvdc_mail_v2.duckdb")
_DB_TMP  = Path("/tmp/hvdc_mail_v2.duckdb.tmp")

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
        "btn_pdf": "첨부 PDF 열기 (Google Drive)",
        "pdf_folder_alt": "첨부 PDF 폴더 (날짜별로 분할 저장):",
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
        "sem_translate": "한국어 감지 → 영어로 번역 중...",
        "sem_translated": "번역된 검색어",
        "sem_no_key_translate": "Gemini API 키 없음 — 원문으로 검색합니다.",
        "bm25_translate": "한국어 감지 → 영어 번역 후 키워드 검색:",
        "btn_bulk_summary": "AI 일괄 요약 (상위 10건)",
        "bulk_summary_spinner": "Gemini 분석 중...",
        "bulk_summary_header": "검색 결과 AI 요약",
        "query_rewrite": "쿼리 확장 사용 (Gemini)",
        "query_rewrite_caption": "확장된 검색어:",
        "refine_placeholder": "결과 좁히기 (예: 2025년만, DSV만)",
        "btn_similar": "유사 이메일 5건",
        "btn_timeline": "Case 타임라인",
        "btn_sender_history": "발신자 히스토리",
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
        "btn_pdf": "Open PDF Attachment (Google Drive)",
        "pdf_folder_alt": "PDF Attachment Folders (split by date):",
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
        "sem_translate": "Korean detected — translating to English...",
        "sem_translated": "Translated query",
        "sem_no_key_translate": "No Gemini key — searching with original query.",
        "bm25_translate": "Korean detected → translated for FTS:",
        "btn_bulk_summary": "AI Summary (Top 10)",
        "bulk_summary_spinner": "Gemini summarizing...",
        "bulk_summary_header": "Search Results AI Summary",
        "query_rewrite": "Expand query (Gemini)",
        "query_rewrite_caption": "Expanded query:",
        "refine_placeholder": "Refine results (e.g. 2025 only, DSV only)",
        "btn_similar": "Similar Emails (5)",
        "btn_timeline": "Case Timeline",
        "btn_sender_history": "Sender History",
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
        except Exception:
            pass
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
    return SentenceTransformer("all-MiniLM-L6-v2")


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


def _extract_snippet(body: str, query: str, context_chars: int = 150) -> str:
    if not body or not query:
        return ""
    body_lower = body.lower()
    words = [w for w in query.lower().split() if len(w) > 2]
    best_pos = -1
    for w in words:
        pos = body_lower.find(w)
        if pos != -1 and (best_pos == -1 or pos < best_pos):
            best_pos = pos
    if best_pos == -1:
        return ""
    match_len = len(words[0]) if words else 4
    start = max(0, best_pos - context_chars)
    end = min(len(body), best_pos + match_len + context_chars)
    import re
    snippet = body[start:end].replace("\n", " ").replace("\r", " ").strip()
    for w in words:
        snippet = re.sub(f"(?i)({re.escape(w)})", r"**\1**", snippet)
    return ("…" if start > 0 else "") + snippet + ("…" if end < len(body) else "")


_ENTITY_PATTERNS = {
    "BL":   r'\bBL[-\s]?\d{6,}\b|\bBILL OF LADING\b',
    "PO":   r'\bPO[-\s]?\d{5,}\b|\bPURCHASE ORDER\b',
    "Case": r'\bHVDC[-\s]?\d{3,}\b|\bCASE[-\s]?\d{3,}\b',
    "Site": r'\b(AGI|DAS|MOSB|ADNOC|DSV|Mammoet)\b',
}


def _extract_entities(text: str) -> dict:
    found = {}
    for tag, pattern in _ENTITY_PATTERNS.items():
        matches = list(set(re.findall(pattern, text or "", re.IGNORECASE)))
        if matches:
            found[tag] = matches[:5]
    return found


def _rewrite_query(text: str, api_key: str) -> str:
    """Expand logistics query with HVDC domain synonyms via Gemini Flash."""
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=(
                "You are an HVDC logistics email search assistant. "
                "Expand this search query with relevant synonyms and acronyms "
                "(BL, DEM, DET, DN, MRR, MOSB, DSV, Mammoet, ADNOC, AGI, DAS). "
                "Return ONLY the expanded query, no explanation:\n\n" + text
            ),
        )
        return resp.text.strip()
    except Exception:
        return text


def _translate_ko_to_en(text: str, api_key: str) -> str:
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=(
                "Translate the following Korean text to English for email search. "
                "Return ONLY the translated text, no explanation:\n\n" + text
            ),
        )
        return resp.text.strip()
    except Exception:
        return text


def _is_korean(text: str) -> bool:
    return any("가" <= ch <= "힣" for ch in text)


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
    _qr_api = st.secrets.get("google_api_key", "")
    use_query_rewrite = bool(_qr_api) and st.checkbox(T["query_rewrite"], value=False)

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

    COLS_SHOW = [
        "no", "month", "subject", "sendername", "senderemail",
        "company_name", "recipientto", "deliverytime",
        "site", "stage", "hvdc_cases", "primary_case", "linkkey",
    ]

    WHERE: list[str] = []
    PARAMS: list = []

    google_api_key = st.secrets.get("google_api_key", "")
    bm25_query = query_text
    if query_text and google_api_key and _is_korean(query_text):
        with st.spinner(T["sem_translate"]):
            bm25_query = _translate_ko_to_en(query_text, google_api_key)

    if bm25_query and use_query_rewrite and google_api_key:
        with st.spinner(T["sem_translate"]):
            bm25_query = _rewrite_query(bm25_query, google_api_key)

    if bm25_query:
        WHERE.append("fts_main_emails.match_bm25(no, ?) IS NOT NULL")
        PARAMS.append(bm25_query)

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

    where_clause = ("WHERE " + " AND ".join(WHERE)) if WHERE else ""

    if bm25_query:
        score_col    = ", fts_main_emails.match_bm25(no, ?) AS bm25_score"
        order_by     = "ORDER BY bm25_score DESC"
        extra_params = [bm25_query]
    else:
        score_col    = ""
        order_by     = 'ORDER BY "deliverytime" DESC'
        extra_params = []

    col_list   = ", ".join(f'"{c}"' for c in COLS_SHOW)
    sql        = f"SELECT {col_list}{score_col} FROM emails {where_clause} {order_by} LIMIT ?"
    all_params = PARAMS + extra_params + [max_rows]

    with st.spinner(T["searching"]):
        total_cnt = count_emails(where_clause, tuple(PARAMS))
        df        = run_query(sql, all_params if all_params else None)

    c1, c2, c3 = st.columns(3)
    c1.metric(T["metric_match"], f"{total_cnt:,}", help=T["metric_match_help"])
    c2.metric(T["metric_shown"], f"{len(df):,}",   help=f"{T['metric_shown_help']} {max_rows:,}")
    c3.metric(T["metric_total"], f"{get_total_emails():,}", help=T["metric_total_help"])

    st.divider()
    if bm25_query != query_text:
        st.caption(f"{T['bm25_translate']} `{bm25_query}`")

    if df.empty:
        any_filter = bool(query_text or sel_months or sel_sites or sel_stages
                          or sender_filter or case_filter)
        if any_filter:
            st.info(T["no_results_filter"])
        else:
            st.info(T["no_results_empty"])
    else:
        df_show = df.copy()
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
            df_show["snippet"] = df_show["no"].apply(
                lambda n: _extract_snippet(_bmap.get(str(n), ""), bm25_query) or T["snip_none"]
            )
        if "linkkey" in df_show.columns:
            df_show["pdf_link"] = df_show["linkkey"].apply(
                lambda k: f"https://drive.google.com/drive/search?q={k}"
                if k and str(k).strip() not in ("", "None", "nan") else None
            )
            df_show = df_show.drop(columns=["linkkey"])
        else:
            df_show["pdf_link"] = None

        _snippets = {}
        if "snippet" in df_show.columns:
            _snippets = dict(zip(df_show["no"].astype(str), df_show["snippet"]))
            df_table = df_show.drop(columns=["snippet"])
        else:
            df_table = df_show

        st.dataframe(
            df_table,
            use_container_width=True,
            column_config={
                "subject":      st.column_config.TextColumn(T["col_subject"],  width=280),
                "senderemail":  st.column_config.TextColumn(T["col_sender"],   width=180),
                "deliverytime": st.column_config.TextColumn(T["col_received"], width=140),
                "hvdc_cases":   st.column_config.TextColumn(T["col_cases"],    width=170),
                "bm25_score":   st.column_config.NumberColumn(T["col_score"],  format="%.3f"),
                "pdf_link":     st.column_config.LinkColumn(T["col_pdf"],      display_text="Open", width=70),
            },
            hide_index=True,
            height=500,
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

        st.subheader(T["email_detail"])
        row_no = st.selectbox(
            T["select_email"],
            options=df["no"].tolist()[:50],
            format_func=lambda x: (
                f"#{x}  "
                + (df.loc[df["no"] == x, "subject"].values[0][:60]
                   if not df.loc[df["no"] == x, "subject"].empty else "")
            ),
        )
        if row_no:
            body_df = run_query(
                "SELECT subject, sendername, senderemail, deliverytime, "
                "recipientto, plaintextbody, linkkey, primary_case FROM emails WHERE no = ?",
                [str(row_no)],
            )
            if not body_df.empty:
                r = body_df.iloc[0]
                col_a, col_b = st.columns(2)
                col_a.markdown(f"**{T['col_subject']}**  \n{r['subject']}")
                col_a.markdown(f"**{T['col_sender']}**  \n{r['sendername']}  \n`{r['senderemail']}`")
                col_b.markdown(f"**{T['col_received']}**  \n{r['deliverytime']}")
                col_b.markdown(f"**{T['col_recipients']}**  \n{r['recipientto']}")
                st.text_area(T["col_body"], value=r["plaintextbody"] or f"({T['col_body']} N/A)", height=380)

                _entities = _extract_entities(str(r["plaintextbody"] or ""))
                if _entities:
                    st.markdown("**Entities:**")
                    for _tag, _vals in _entities.items():
                        st.markdown("`" + _tag + "` " + " ".join(f"`{v}`" for v in _vals))

                lk = r.get("linkkey") if hasattr(r, "get") else r["linkkey"]
                if lk and str(lk).strip() not in ("", "None", "nan"):
                    pdf_url = f"https://drive.google.com/drive/search?q={lk}"
                    st.link_button(T["btn_pdf"], pdf_url, type="primary")
                else:
                    st.markdown(f"**{T['pdf_folder_alt']}**")
                    for _label, _url in DRIVE_FOLDERS:
                        st.markdown(f"- [{_label}]({_url})")

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
                            "SELECT embedding FROM emails WHERE no = ?",
                            [str(row_no)],
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
                                    "FROM emails WHERE no != ? AND embedding IS NOT NULL "
                                    "ORDER BY sim_score DESC LIMIT 5",
                                    [_evec, str(row_no)],
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

        st.divider()
        st.download_button(
            T["csv_download"],
            data=df.to_csv(index=False).encode("utf-8-sig"),
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
            _embed_query = sem_query
            if any('가' <= c <= '힣' for c in sem_query):
                if google_api_key:
                    with st.spinner(T["sem_translate"]):
                        _embed_query = _translate_ko_to_en(sem_query, google_api_key)
                    st.caption(f"{T['sem_translated']}: **{_embed_query}**")
                else:
                    st.caption(T["sem_no_key_translate"])
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
                        bm25_df = run_query(
                            f"SELECT no, fts_main_emails.match_bm25(no, ?) AS bm25_score "
                            f"FROM emails ORDER BY bm25_score DESC LIMIT {sem_top_k * 2}",
                            [sem_query],
                        )
                        if not bm25_df.empty and not vec_df.empty:
                            bm25_max = float(bm25_df["bm25_score"].max() or 1)
                            bm25_df["bm25_norm"] = bm25_df["bm25_score"] / bm25_max
                            merged = vec_df.merge(bm25_df[["no", "bm25_norm"]], on="no", how="left").fillna(0)
                            merged["hybrid_score"] = (
                                0.7 * merged["cosine_score"] + 0.3 * merged["bm25_norm"]
                            )
                            result_df = merged.sort_values("hybrid_score", ascending=False).head(sem_top_k)
                            score_col_name = "hybrid_score"
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
                    st.dataframe(
                        result_df,
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

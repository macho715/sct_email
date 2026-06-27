"""
HVDC Email Search — Streamlit + DuckDB  v2.0
Features: BM25 Search | Gemini AI Summary | Case Thread | Network Graph | Anomaly Alerts | Semantic Search
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

# ─────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="HVDC Email Search",
    page_icon="✉",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 비밀번호 보호 ─────────────────────────────────────────────────────
_PASSWORD = st.secrets.get("password", "")
if _PASSWORD:
    _input_pwd = st.text_input("🔒 비밀번호를 입력하세요", type="password")
    if _input_pwd != _PASSWORD:
        st.warning("올바른 비밀번호를 입력해야 대시보드를 사용할 수 있습니다.")
        st.stop()

st.markdown("""
<style>
[data-testid="stSidebar"] { background: #F7F9FC; }
[data-testid="stSidebar"] * { color: #1E293B !important; }
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stMultiSelect label,
[data-testid="stSidebar"] .stTextInput label,
[data-testid="stSidebar"] .stSlider label { color: #374151 !important; }
[data-testid="stMetricValue"]  { color: #1F5276; font-size: 1.55rem; font-weight: 700; }
[data-testid="stMetricLabel"]  {
    font-size: .75rem; color: #64748B; font-weight: 600;
    text-transform: uppercase; letter-spacing: .04em;
}
/* Tab active indicator */
.stTabs [role="tab"] { font-weight: 500; }
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    border-bottom: 3px solid #1F5276;
    color: #1F5276;
}
.stButton > button:focus-visible,
[data-testid="stDownloadButton"] > button:focus-visible {
    outline: 2px solid #1F5276;
    outline-offset: 2px;
}
[data-testid="stDownloadButton"] > button {
    background: #1F5276; color: white;
    border: none; border-radius: 6px;
    padding: 0.4rem 1rem;
}
[data-testid="stDownloadButton"] > button:hover { background: #2E86C1; }
div[data-testid="stAlert"] { border-radius: 8px; }
[data-testid="stDataFrame"] { border-radius: 8px; }
/* Sidebar section card */
.sidebar-section {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 12px 14px;
    margin-bottom: 10px;
}
/* Sidebar section label */
.sidebar-label {
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #2471A3;
    margin-bottom: 6px;
}
/* AI summary branded card */
.ai-summary-card {
    background: #E8F4FD;
    border-left: 4px solid #1F5276;
    border-radius: 0 8px 8px 0;
    padding: 14px 16px;
    margin-top: 8px;
    white-space: pre-wrap;
    font-size: 0.9rem;
    line-height: 1.6;
    color: #1E293B;
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
        st.error(f"쿼리 오류: {e}")
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


# ── Feature 5: 이상 탐지 ─────────────────────────────────────────
@st.cache_data(ttl=3600)
def get_anomaly_alerts() -> pd.DataFrame:
    return run_query("""
        WITH weekly AS (
            SELECT company_name,
                   COUNT(*) FILTER (
                       WHERE TRY_CAST(deliverytime AS DATE) >= CURRENT_DATE - INTERVAL '7 days'
                   ) AS recent,
                   COUNT(*) FILTER (
                       WHERE TRY_CAST(deliverytime AS DATE) >= CURRENT_DATE - INTERVAL '35 days'
                         AND TRY_CAST(deliverytime AS DATE) <  CURRENT_DATE - INTERVAL '7 days'
                   ) / 4.0 AS avg4w
            FROM emails
            WHERE company_name IS NOT NULL
            GROUP BY company_name
        )
        SELECT company_name, recent, ROUND(avg4w, 1) AS avg4w
        FROM weekly
        WHERE (avg4w > 3 AND recent < avg4w * 0.3)
           OR (recent > avg4w * 3 AND avg4w > 3)
        ORDER BY ABS(recent - avg4w) DESC
        LIMIT 5
    """)


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
            return "⚠️ Gemini API 월 지출 한도 초과. https://aistudio.google.com/app/apikey 에서 한도를 높이거나 다음 달에 다시 시도하세요."
        return f"오류: {e}"


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
        st.error(f"임베딩 오류: {e}")
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


# ── 헤더 ─────────────────────────────────────────────────────────
st.title("✉ HVDC Email Search")
st.caption("OUTLOOK HVDC 전체 이메일 데이터 — DuckDB FTS · Gemini AI · Samsung C&T / ADNOC")

# ── DB 초기화 (atomic, top-level) ────────────────────────────────
if _DB_TMP.exists():
    _DB_TMP.unlink(missing_ok=True)

if not DB_LOCAL.exists():
    _download_error = None
    with st.status("DB 초기화 중...", expanded=True) as _status:
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
            _status.update(label="✅ DB 준비 완료!", state="complete")
        except Exception as _exc:
            _DB_TMP.unlink(missing_ok=True)
            _download_error = str(_exc)
            _status.update(label="❌ 다운로드 실패", state="error")
    if _download_error:
        st.error(f"DB 다운로드 실패: {_download_error}")
        st.stop()
    else:
        st.rerun()

months, sites, stages = load_filter_options()

# ── 첨부파일 폴더 링크 ────────────────────────────────────────────
DRIVE_FOLDERS = [
    ("📁 첨부파일 폴더 1 (Apr 2026 초)",  "https://drive.google.com/drive/folders/1nGE7Ldq8aC0ut8ZuiA8aCUa77f362DxK"),
    ("📁 첨부파일 폴더 2 (Apr-May 2026)", "https://drive.google.com/drive/folders/1FwcHBvKqy12CqHMPcEOp09y0J8stLZZ2"),
    ("📁 첨부파일 폴더 3 (May 2026)",     "https://drive.google.com/drive/folders/1gmpdc7MUeWXv0T5mitUemF2EKzcCRSDH"),
    ("📁 첨부파일 폴더 4 (Jun 2026 초)",  "https://drive.google.com/drive/folders/1Th_BvMreMVvGdfrQTzp5gUDpKi0f1I63"),
    ("📁 첨부파일 폴더 5 (Jun 2026 최신)","https://drive.google.com/drive/folders/1btH18NykL9wDKKuJZZBTSUGCsYkXcaxm"),
]

# ── 사이드바 ────────────────────────────────────────────────────────
with st.sidebar:
    # 이상 탐지 알림 섹션
    alert_df = get_anomaly_alerts()
    if not alert_df.empty:
        st.markdown('<div class="sidebar-label">이상 탐지 알림</div>', unsafe_allow_html=True)
        for _, row in alert_df.iterrows():
            company = row["company_name"]
            recent  = int(row["recent"])
            avg4w   = float(row["avg4w"])
            if avg4w > 0 and recent > avg4w * 3:
                st.error(f"**{company}** — 최근 7일 {recent}건 (평균 {avg4w}건, **{recent/avg4w:.1f}배** 급증)")
            else:
                st.warning(f"**{company}** — 최근 7일 {recent}건 (평균 {avg4w}건, 급감)")
        st.divider()

    # 필터 섹션
    st.markdown('<div class="sidebar-label">검색 및 필터</div>', unsafe_allow_html=True)

    query_text = st.text_input(
        "키워드 검색 (FTS)",
        placeholder="예: DSV, cable, 5000684244",
        help="Subject · SenderName · Body · HVDC Cases 전체 텍스트 검색",
    )

    sel_months = st.multiselect("Month", months, help="202410 = 2024년 10월")
    sel_sites  = st.multiselect("Site",  sites)
    sel_stages = st.multiselect("Stage", stages)

    with st.expander("고급 필터"):
        sender_filter = st.text_input("발신자 이메일 포함", placeholder="@dsv.com")
        case_filter   = st.text_input("HVDC Case 번호", placeholder="HVDC-ADOPT-SEI-0008")

    max_rows = st.slider("최대 결과 수", 50, 2000, 200, 50)

    st.divider()

    # 첨부파일 폴더 섹션
    st.markdown('<div class="sidebar-label">PDF 첨부파일 폴더</div>', unsafe_allow_html=True)
    for _label, _url in DRIVE_FOLDERS:
        st.markdown(f"[{_label}]({_url})")

    st.divider()
    with st.expander("DB 진단", expanded=False):
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

    _confirm_reset = st.checkbox("DB 재다운로드를 확인합니다 (기존 캐시가 모두 삭제됩니다)")
    if st.button("캐시 초기화 + DB 재다운로드", use_container_width=True, disabled=not _confirm_reset):
        st.cache_data.clear()
        st.cache_resource.clear()
        DB_LOCAL.unlink(missing_ok=True)
        _DB_TMP.unlink(missing_ok=True)
        st.rerun()


# ── 탭 (3개) ─────────────────────────────────────────────────────
tab_search, tab_analytics, tab_semantic = st.tabs(["검색", "분석", "시맨틱 검색"])


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

    if query_text:
        WHERE.append("fts_main_emails.match_bm25(no, ?) IS NOT NULL")
        PARAMS.append(query_text)

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

    if query_text:
        score_col    = ", fts_main_emails.match_bm25(no, ?) AS bm25_score"
        order_by     = "ORDER BY bm25_score DESC"
        extra_params = [query_text]
    else:
        score_col    = ""
        order_by     = 'ORDER BY "deliverytime" DESC'
        extra_params = []

    col_list   = ", ".join(f'"{c}"' for c in COLS_SHOW)
    sql        = f"SELECT {col_list}{score_col} FROM emails {where_clause} {order_by} LIMIT ?"
    all_params = PARAMS + extra_params + [max_rows]

    with st.spinner("조회 중..."):
        total_cnt = count_emails(where_clause, tuple(PARAMS))
        df        = run_query(sql, all_params if all_params else None)

    c1, c2, c3 = st.columns(3)
    c1.metric("매칭 건수",    f"{total_cnt:,}",        help="현재 필터 조건과 일치하는 이메일 수")
    c2.metric("표시 결과",    f"{len(df):,}",           help=f"최대 {max_rows:,}건 제한")
    c3.metric("DB 총 이메일", f"{get_total_emails():,}", help="전체 데이터베이스 보유량")

    st.divider()

    if df.empty:
        any_filter = bool(query_text or sel_months or sel_sites or sel_stages
                          or sender_filter or case_filter)
        if any_filter:
            st.info(
                "검색 결과가 없습니다.\n\n"
                "- 키워드 철자를 확인하거나 더 짧은 단어로 검색해보세요.\n"
                "- 필터 조건을 줄이면 더 많은 결과가 나올 수 있습니다."
            )
        else:
            st.info("왼쪽 사이드바에서 키워드 또는 필터를 입력하면 이메일을 검색합니다.")
    else:
        # linkkey → Google Drive search URL
        df_show = df.copy()
        if "linkkey" in df_show.columns:
            df_show["pdf_link"] = df_show["linkkey"].apply(
                lambda k: f"https://drive.google.com/drive/search?q={k}"
                if k and str(k).strip() not in ("", "None", "nan") else None
            )
            df_show = df_show.drop(columns=["linkkey"])
        else:
            df_show["pdf_link"] = None

        st.dataframe(
            df_show,
            use_container_width=True,
            column_config={
                "subject":      st.column_config.TextColumn("제목",       width=280),
                "senderemail":  st.column_config.TextColumn("발신자",     width=180),
                "deliverytime": st.column_config.TextColumn("수신일시",   width=140),
                "hvdc_cases":   st.column_config.TextColumn("HVDC Cases", width=170),
                "bm25_score":   st.column_config.NumberColumn("관련도", format="%.3f"),
                "pdf_link":     st.column_config.LinkColumn("📄 PDF", display_text="열기", width=70),
            },
            hide_index=True,
            height=500,
        )

        st.subheader("본문 보기")
        row_no = st.selectbox(
            "메일 선택 (no 번호)",
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
                col_a.markdown(f"**제목**  \n{r['subject']}")
                col_a.markdown(f"**발신자**  \n{r['sendername']}  \n`{r['senderemail']}`")
                col_b.markdown(f"**수신일시**  \n{r['deliverytime']}")
                col_b.markdown(f"**수신자**  \n{r['recipientto']}")
                st.text_area("본문", value=r["plaintextbody"] or "(본문 없음)", height=380)

                # PDF 링크
                lk = r.get("linkkey") if hasattr(r, "get") else r["linkkey"]
                if lk and str(lk).strip() not in ("", "None", "nan"):
                    pdf_url = f"https://drive.google.com/drive/search?q={lk}"
                    st.link_button("📄 첨부 PDF 열기 (Google Drive)", pdf_url, type="primary")
                else:
                    st.markdown("📎 **첨부 PDF 폴더** (날짜별로 분할 저장):")
                    for _label, _url in DRIVE_FOLDERS:
                        st.markdown(f"- [{_label}]({_url})")

                # Feature 1: Gemini AI 요약
                google_api_key = st.secrets.get("google_api_key", "")
                if google_api_key:
                    if st.button("🤖 AI 요약 (Gemini)", key=f"gemini_{row_no}"):
                        with st.spinner("Gemini 분석 중..."):
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
                    st.caption("💡 Gemini AI 요약을 사용하려면 Streamlit Secrets에 `google_api_key`를 추가하세요.")

                # Feature 3: Case 스레드 타임라인
                primary_case_val = r.get("primary_case") if hasattr(r, "get") else r["primary_case"]
                if primary_case_val and str(primary_case_val).strip() not in ("", "None", "nan"):
                    with st.expander(f"📋 케이스 스레드: {primary_case_val}"):
                        thread_df = run_query(
                            "SELECT no, deliverytime, subject, sendername FROM emails "
                            "WHERE primary_case = ? ORDER BY deliverytime",
                            [str(primary_case_val)],
                        )
                        if not thread_df.empty:
                            st.caption(f"이 케이스 관련 이메일 총 **{len(thread_df)}건**")
                            fig_thread = px.scatter(
                                thread_df,
                                x="deliverytime",
                                y="sendername",
                                hover_data=["subject", "no"],
                                title=f"스레드 타임라인 — {primary_case_val}",
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
                                    "subject": st.column_config.TextColumn("제목", width=300),
                                },
                            )

        st.divider()
        st.download_button(
            "결과 CSV 다운로드",
            data=df.to_csv(index=False).encode("utf-8-sig"),
            file_name="hvdc_email_search_result.csv",
            mime="text/csv",
        )


# ════════════════════════════════════════════════════════════════
# TAB 2 — 분석 (기존 + Feature 4: 네트워크 그래프)
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
                    '미분류'
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
                COALESCE(NULLIF(TRIM(site), ''), '미분류') AS site,
                COUNT(*) AS email_count
            FROM emails
            GROUP BY site
            ORDER BY email_count DESC
        """)
        stage_df = run_query("""
            SELECT
                COALESCE(NULLIF(TRIM(stage), ''), '미분류') AS stage,
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
    metric_total.metric("분석 이메일", f"{total_volume:,}")
    metric_peak.metric("피크 월", peak_month, f"{peak_count:,}건" if peak_count else None)
    metric_sites.metric("Site", f"{len(site_df):,}")
    metric_stages.metric("Stage", f"{len(stage_df):,}")

    if not analytics_export_df.empty:
        st.download_button(
            "Analytics CSV 다운로드",
            data=analytics_export_df.to_csv(index=False).encode("utf-8-sig"),
            file_name="hvdc_email_analytics.csv",
            mime="text/csv",
        )

    # 서브탭
    sub_vol, sub_heat, sub_dist, sub_network = st.tabs([
        "📈 월별 추이",
        "🗺️ Site × 월 히트맵",
        "📊 Site / Stage 분포",
        "🕸️ 네트워크",
    ])

    with sub_vol:
        st.subheader("월별 이메일 수신량")
        if vol_df.empty:
            st.info("월별 데이터가 없습니다.")
        else:
            fig_vol = px.bar(
                vol_df, x="month", y="email_count",
                labels={"month": "연월", "email_count": "이메일 수"},
                color="email_count",
                color_continuous_scale=_SEQ,
            )
            fig_vol.update_layout(
                **_CHART,
                showlegend=False,
                coloraxis_showscale=False,
                height=340,
                xaxis=dict(title="연월", tickangle=-45, type="category", tickfont=dict(size=11)),
                yaxis=dict(title="이메일 수", gridcolor="#E5E7EB"),
            )
            fig_vol.update_traces(hovertemplate="<b>%{x}</b><br>이메일 수: %{y:,}<extra></extra>")
            st.plotly_chart(fig_vol, use_container_width=True)

            _, col_top = st.columns([3, 2])
            with col_top:
                st.subheader("Top 20 발신 그룹")
                if not top_df.empty:
                    fig_top = px.bar(
                        top_df, x="email_count", y="sender_group",
                        orientation="h",
                        labels={"email_count": "이메일 수", "sender_group": ""},
                        color="email_count",
                        color_continuous_scale=_SEQ,
                    )
                    fig_top.update_layout(
                        **_CHART,
                        showlegend=False,
                        coloraxis_showscale=False,
                        yaxis=dict(categoryorder="total ascending"),
                        xaxis=dict(title="이메일 수", gridcolor="#E5E7EB"),
                        height=400,
                    )
                    fig_top.update_traces(hovertemplate="<b>%{y}</b><br>이메일 수: %{x:,}<extra></extra>")
                    st.plotly_chart(fig_top, use_container_width=True)

            with st.expander("월별 원시 데이터"):
                st.dataframe(vol_df, use_container_width=True, hide_index=True)

    with sub_heat:
        st.subheader("Site × 월 히트맵")
        if heat_df.empty:
            st.info("Site 또는 월 데이터가 없습니다.")
        else:
            pivot = heat_df.pivot_table(
                index="site", columns="month",
                values="email_count", fill_value=0,
            )
            pivot.columns = [str(c) for c in pivot.columns]
            fig_heat = px.imshow(
                pivot,
                labels={"x": "연월", "y": "Site", "color": "이메일 수"},
                color_continuous_scale=_SEQ,
                aspect="auto",
                text_auto=False,
            )
            fig_heat.update_layout(
                **_CHART,
                height=400,
                xaxis=dict(type="category", tickangle=-45, tickfont=dict(size=12)),
            )
            fig_heat.update_traces(hovertemplate="<b>%{y}</b> · %{x}<br>이메일 수: %{z:,}<extra></extra>")
            st.plotly_chart(fig_heat, use_container_width=True)

    with sub_dist:
        st.subheader("Site / Stage 분포")
        col_site, col_stage = st.columns(2)

        with col_site:
            if site_df.empty:
                st.info("Site 데이터가 없습니다.")
            else:
                fig_site = px.pie(
                    site_df.head(12),
                    names="site",
                    values="email_count",
                    color_discrete_sequence=_PIE_COLORS,
                )
                fig_site.update_traces(
                    hole=0.45,
                    hovertemplate="<b>%{label}</b><br>이메일 수: %{value:,}<extra></extra>",
                )
                fig_site.update_layout(**_CHART, height=360, legend_title_text="Site")
                st.plotly_chart(fig_site, use_container_width=True)

        with col_stage:
            if stage_df.empty:
                st.info("Stage 데이터가 없습니다.")
            else:
                fig_stage = px.pie(
                    stage_df.head(12),
                    names="stage",
                    values="email_count",
                    color_discrete_sequence=_PIE_COLORS,
                )
                fig_stage.update_traces(
                    hole=0.45,
                    hovertemplate="<b>%{label}</b><br>이메일 수: %{value:,}<extra></extra>",
                )
                fig_stage.update_layout(**_CHART, height=360, legend_title_text="Stage")
                st.plotly_chart(fig_stage, use_container_width=True)

        st.dataframe(
            analytics_export_df,
            use_container_width=True,
            hide_index=True,
            height=320,
            column_config={
                "metric": st.column_config.TextColumn("집계", width=160),
                "dimension": st.column_config.TextColumn("항목", width=220),
                "count": st.column_config.NumberColumn("이메일 수", format="%d"),
            },
        )

    # Feature 4: 네트워크 그래프
    with sub_network:
        st.subheader("회사 이메일 네트워크")
        st.caption("발신 회사 → 수신 도메인 흐름 (5건 이상만 표시)")

        net_df = load_network_data()
        if net_df.empty:
            st.info("네트워크 데이터가 없습니다.")
        else:
            try:
                import networkx as nx

                G = nx.from_pandas_edgelist(
                    net_df, source="source", target="target",
                    edge_attr="weight", create_using=nx.DiGraph()
                )

                @st.cache_data(show_spinner=False)
                def _compute_layout(_edge_list: list) -> dict:
                    _G = nx.from_edgelist(_edge_list, create_using=nx.DiGraph())
                    return nx.spring_layout(_G, seed=42, k=2.0)

                pos = _compute_layout(list(G.edges()))

                edge_traces = []
                for u, v, data in G.edges(data=True):
                    x0, y0 = pos[u]
                    x1, y1 = pos[v]
                    w = data.get("weight", 1)
                    edge_traces.append(go.Scatter(
                        x=[x0, x1, None], y=[y0, y1, None],
                        mode="lines",
                        line=dict(width=min(w / 20, 5), color="#5DADE2"),
                        hoverinfo="none",
                        showlegend=False,
                    ))

                node_x = [pos[n][0] for n in G.nodes()]
                node_y = [pos[n][1] for n in G.nodes()]
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
                        colorbar=dict(title="연결 수", thickness=12),
                        line=dict(width=1, color="#FFFFFF"),
                    ),
                    hovertemplate="<b>%{text}</b><br>연결 수: %{marker.size}<extra></extra>",
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
                # networkx 미설치 시 간단한 chord-style bar 대체
                st.info("networkx 미설치 — 상위 연결 현황으로 대체 표시합니다. `pip install networkx`")
                top_net = net_df.sort_values("weight", ascending=False).head(30)
                top_net["link"] = top_net["source"] + " → " + top_net["target"]
                fig_fallback = px.bar(
                    top_net, x="weight", y="link", orientation="h",
                    labels={"weight": "이메일 수", "link": ""},
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
                    "source": st.column_config.TextColumn("발신 회사", width=200),
                    "target": st.column_config.TextColumn("수신 도메인", width=200),
                    "weight": st.column_config.NumberColumn("이메일 수", format="%d"),
                },
            )


# ════════════════════════════════════════════════════════════════
# TAB 3 — 시맨틱 검색 (Feature 2 + 6)
# ════════════════════════════════════════════════════════════════
with tab_semantic:
    st.subheader("시맨틱 검색 (all-MiniLM-L6-v2, 384 dim)")

    _has_emb = has_embeddings()
    if not _has_emb:
        st.info(
            "임베딩 데이터가 없습니다. 로컬에서 `build_db.py`를 실행하여 DB를 재빌드하세요:\n\n"
            "```bash\n"
            "python build_db.py\n"
            "```\n\n"
            "완료 후 GitHub Release에 v2.0으로 재업로드하고 `DB_URL`을 업데이트하세요."
        )
    else:
        google_api_key = st.secrets.get("google_api_key", "")
        sem_query = st.text_input(
            "의미 기반 검색어",
            placeholder="예: transformer installation schedule delay",
            help="정확한 키워드 대신 의미로 검색합니다",
        )
        sem_top_k = st.slider("결과 수", 10, 100, 30, 10)
        use_hybrid = st.checkbox("BM25 + 시맨틱 Hybrid (권장)", value=True)

        if sem_query and st.button("시맨틱 검색 실행"):
            with st.spinner("임베딩 생성 중..."):
                qvec = get_query_embedding(sem_query)

            if qvec:
                with st.spinner("벡터 검색 중..."):
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
                        st.warning("결과 없음 — 다른 검색어를 시도하거나 Hybrid 모드를 켜세요.")
                    else:
                        st.success(f"검색 완료 — {len(result_df)}건")
                    st.dataframe(
                        result_df,
                        use_container_width=True,
                        hide_index=True,
                        height=500,
                        column_config={
                            "subject":       st.column_config.TextColumn("제목", width=200),
                            "sendername":    st.column_config.TextColumn("발신자", width=150),
                            "deliverytime":  st.column_config.TextColumn("수신일시", width=140),
                            "company_name":  st.column_config.TextColumn("회사", width=150),
                            score_col_name:  st.column_config.NumberColumn("유사도", format="%.4f"),
                        },
                    )

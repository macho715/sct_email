# HVDC Email Search

Samsung C&T HVDC 프로젝트 이메일 검색 대시보드 (Abu Dhabi / ADNOC).  
Streamlit + DuckDB · BM25 Full-Text Search · Semantic Vector Search · Analytics

**Live App → [hvdc-mail.streamlit.app](https://hvdc-mail.streamlit.app)**  
Password: `hvdc2024` — 팀원 누구나 브라우저에서 바로 접속 가능 (Google 인증 불필요)

---

## Features

| Tab | 기능 |
|-----|------|
| **Search** | BM25 Full-Text Search — 제목 / 발신자 / 본문 / HVDC Case 번호 키워드 검색 |
| **Analytics** | 월별 트렌드, 사이트×월 Heatmap, Site/Stage 분포, 회사 Email Network 그래프 |
| **Semantic Search** | 벡터 유사도 검색 — `all-MiniLM-L6-v2` (384 dim, API 키 불필요), BM25 Hybrid |

- **KO / EN 언어 전환** — 사이드바 버튼으로 전체 UI 언어 즉시 변경
- **Gemini AI 요약** — 이메일 상세 뷰에서 선택적 AI 요약 (Google API Key 옵션)
- **CSV 다운로드** — 검색 결과 및 Analytics 데이터 내보내기

---

## 데이터 규모

| 항목 | 값 |
|------|----|
| 총 이메일 수 | **51,964** 건 |
| 기간 | 2024-01 ~ 2026-06 |
| DB 크기 | 448 MB (DuckDB) |
| 임베딩 | 384-dim HNSW cosine index |

---

## 팀원 접속 방법

1. 브라우저에서 **https://hvdc-mail.streamlit.app** 열기
2. 비밀번호 `hvdc2024` 입력
3. 검색 / 분석 시작

별도 설치 없음. Google Cloud / GitHub 계정 불필요. 모바일 브라우저도 지원.

---

## Local Setup (개발용)

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
# .venv/bin/activate        # Mac/Linux
pip install -r requirements.txt
```

### DB 빌드 (최초 1회, ~60분)

`OUTLOOK_HVDC_*.xlsx`를 프로젝트 폴더에 두고 실행:

```bash
python build_db.py
```

`hvdc_mail.duckdb` 생성 (FTS + HNSW + 384-dim 임베딩 포함).

### 로컬 실행

```bash
streamlit run app.py
# http://localhost:8501
```

---

## Cloud Deployment

앱 시작 시 **GitHub Releases v2.0**에서 `hvdc_mail.duckdb`를 자동 다운로드.  
Semantic Search는 `sentence-transformers`로 서버에서 실행 (Google API Key 불필요).

### Streamlit Cloud Secrets (git에 커밋하지 않음)

Streamlit Cloud 대시보드 → App Settings → Secrets:

```toml
google_api_key = "AIza..."   # Gemini AI 요약 (선택)
password = "hvdc2024"        # 앱 접근 비밀번호
```

### DB 갱신 및 재배포 절차

```bash
# 1. DB 재빌드
python build_db.py

# 2. GitHub Release에 새 DB 업로드
gh release create v3.0 hvdc_mail.duckdb --title "v3.0 YYYY-MM"

# 3. app.py의 DB_URL을 v3.0으로 수정 후 커밋
git add app.py && git commit -m "chore: bump DB_URL to v3.0"
git push origin main   # → Streamlit Cloud 자동 재배포
```

---

## Architecture

```
app.py                  Streamlit UI + DuckDB 쿼리 (read-only)
build_db.py             Excel → DuckDB + FTS + 임베딩 + HNSW 인덱스
requirements.txt        Streamlit Cloud 런타임 의존성
.streamlit/
  config.toml           테마 (Samsung C&T navy)
  secrets.toml          API 키 — gitignore, Streamlit Cloud 대시보드에서 설정
```

---

## DB Schema (emails 테이블, 51,964 rows)

주요 컬럼: `no`, `subject`, `sendername`, `senderemail`, `deliverytime`,  
`plaintextbody`, `hvdc_cases`, `company_name`, `site`, `stage`, `month`,  
`embedding FLOAT[384]`

인덱스: B-tree (`idx_month`, `idx_stage`, `idx_site`),  
HNSW cosine (`idx_embedding_hnsw`), BM25 FTS (7개 컬럼).

---

## Notes

- `hvdc_mail.duckdb` (448 MB) — gitignore 처리, GitHub Releases로 배포
- `OUTLOOK_HVDC_*.xlsx` — gitignore 처리 (내부 민감 데이터)
- Streamlit Cloud 무료 티어: RAM 1 GB, 최초 시맨틱 검색 시 모델 로드 ~5초
- Anomaly Detection 기능은 v2.1에서 제거됨

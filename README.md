# HVDC Email Search

Samsung C&T HVDC 프로젝트 **과거 이메일 검색** 플랫폼 (Abu Dhabi / ADNOC).  
"2024년에 DSV가 보낸 DEM 관련 이메일 찾아줘" — 자연어로 51,964건 이메일을 즉시 검색.  
Streamlit + DuckDB · BM25 Full-Text Search · Semantic Vector Search · Analytics

**Live App → [hvdc-mail.streamlit.app](https://hvdc-mail.streamlit.app)**  
Password: `hvdc2024` — 팀원 누구나 브라우저에서 바로 접속 가능 (Google 인증 불필요)

---

## Core Focus — 과거 이메일 검색

HVDC 물류 이메일은 **계약·클레임·통관 증빙**의 원천이다.  
이 앱의 핵심 목표: 수만 건의 과거 이메일에서 **필요한 것을 10초 안에 찾는다**.

| 검색 방식 | 언제 사용 |
|-----------|-----------|
| **키워드 (BM25)** | BL 번호, Case 번호, 발신자 이름 등 정확한 텍스트 |
| **의미 검색 (Vector)** | "DEM 클레임 협상", "통관 지연 사유" 등 개념·의도 기반 |
| **Hybrid** | 두 방식 결합 — 가장 높은 재현율 |

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

## AI 기능 로드맵 (Updated: 2026-06-28)

과거 이메일 검색 경험을 강화할 AI 기능 아이디어. 우선순위 순서.

### P1 — 검색 정확도 향상 (단기)

| 기능 | 설명 | 구현 난이도 |
|------|------|-------------|
| **Query Rewriting** | "DEM 클레임" → 자동으로 "Demurrage claim detention DSV" 확장 후 BM25 재검색. Gemini Flash로 쿼리 전처리. | 낮음 |
| **Smart Snippet** | 검색 결과 카드에 쿼리와 가장 관련 높은 본문 2줄 자동 하이라이트 | 낮음 |
| **Entity Auto-Tag** | 본문에서 BL번호·PO번호·사이트명 자동 추출 → 필터 칩으로 표시 | 중간 |

### P2 — 대화형 검색 (중기)

| 기능 | 설명 |
|------|------|
| **Multi-turn Search** | "이전 결과에서 2025년 것만", "같은 발신자의 다른 이메일" 등 후속 질문으로 검색 범위 좁히기 |
| **Similar Email Finder** | 이메일 상세 뷰에서 "이 건과 유사한 과거 이메일 더 보기" (HNSW cosine 기반) |
| **Timeline Reconstruction** | Case 번호 또는 발신자 조합으로 관련 이메일을 시간순 스레드로 재구성 |

### P3 — 분석·인사이트 (장기)

| 기능 | 설명 |
|------|------|
| **Search Result Summary** | 검색 결과 N건을 Gemini가 "핵심 내용 3줄 요약" — 클레임 히스토리 파악용 |
| **Issue Clustering** | 유사 이슈 이메일을 자동 군집화 (DEM·통관·선적 지연 등 카테고리) |
| **Key Decision Finder** | "이 프로젝트에서 가장 중요한 의사결정 이메일 10건" 추천 |
| **Natural Language Query** | "2025년 3월에 Mammoet가 보낸 MRR 관련 이메일" → SQL 자동 변환 (Text-to-SQL) |

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

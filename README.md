# HVDC Email Search

Samsung C&T HVDC 프로젝트 **과거 이메일 검색** 플랫폼 (Abu Dhabi / ADNOC).  
"2024년에 DSV가 보낸 DEM 관련 이메일 찾아줘" — 자연어로 51,964건 이메일을 즉시 검색.  
Streamlit + DuckDB · BM25 Full-Text Search · Semantic Vector Search · Search Copilot · Google Drive PDF Attachments

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

## Latest Updates (2026-06-29)

최근 모바일 사용과 본문 상세 조회에서 확인된 문제를 반영했다.

| 항목 | 업데이트 내용 |
|------|---------------|
| **모바일 접근성** | 모바일 화면에서도 사이드바가 숨겨지지 않도록 수정했다. |
| **no / month 표시** | `51964.0`, `202606.0`처럼 보이던 값을 `51964`, `202606` 형식으로 정리했다. |
| **본문 보기** | 메일 선택 번호를 정규화해 선택한 이메일 본문이 안정적으로 표시되도록 수정했다. |
| **PDF 첨부 연결** | 본문 보기에서 해당 메일의 Google Drive PDF가 있으면 `첨부 PDF 열기`와 `PDF 다운로드` 버튼을 표시한다. |
| **모바일 PDF 버튼** | 표 안의 작은 링크 외에 `PDF 빠른 열기` 섹션을 추가해 휴대폰에서도 누르기 쉽게 했다. |
| **Exact Identifier Search** | `5000684244`, `HVDC-ADOPT-SEI-0008`, `LPO-1088`, `rowkey` 같은 식별자를 BM25와 별도 경로로 검색한다. |
| **RRF Search Copilot** | BM25, semantic, exact hit, field hit, entity, 최신성 신호를 RRF 기반으로 결합하고 `검색 이유`를 표시한다. |

PDF 연결은 정확한 `linkkey`, 본문/제목 안의 12자리 `linkkey`, 또는 본문 안의 Google Drive 파일 URL을 기준으로 한다.
잘못된 PDF 연결을 막기 위해 제목 유사도만으로 추정 연결하지 않는다.

---

## Features

| Tab | 기능 |
|-----|------|
| **Search** | BM25 Full-Text Search — 제목 / 발신자 / 본문 / HVDC Case 번호 키워드 검색 |
| **Analytics** | 월별 트렌드, 사이트×월 Heatmap, Site/Stage 분포, 회사 Email Network 그래프 |
| **Semantic Search** | 벡터 유사도 검색 — `all-MiniLM-L6-v2` (384 dim, API 키 불필요), BM25 Hybrid |

- **KO / EN 언어 전환** — 사이드바 버튼으로 전체 UI 언어 즉시 변경
- **Search Copilot** — 검색 결과를 BM25, 엔티티, 최신성 신호로 재정렬
- **Exact Identifier Search** — no, HVDC case, LPO, rowkey, linkkey, 본문 내 긴 식별자를 별도 경로로 검색
- **RRF Hybrid Ranking** — BM25와 semantic 점수 스케일 차이를 줄이기 위해 순위 기반 fusion 적용
- **검색 이유 표시** — 결과 표에 exact hit, case/subject/sender/pdf hit 이유 표시
- **도메인 검색어 확장** — `기성`, `통관`, `디머리지` 등 한국어 물류 용어를 영어 도메인 키워드로 확장
- **Smart Snippet** — 검색 결과의 관련 본문 발췌 표시
- **Entity Auto-Tag** — Site, Vendor, Doc, Issue, Ref 등 주요 항목 추출
- **본문 보기** — 선택한 이메일의 제목, 발신자, 수신자, 본문, 관련 PDF 첨부 확인
- **Google Drive PDF 열기 / 다운로드** — 메일별 첨부 PDF가 있으면 상세 화면과 검색 결과에서 직접 연결
- **Gemini AI 요약** — 이메일 상세 뷰에서 선택적 AI 요약 (Google API Key 옵션)
- **CSV 다운로드** — 검색 결과 및 Analytics 데이터 내보내기

---

## AI 기능 현황 (Updated: 2026-06-29)

과거 이메일 검색 경험을 강화하기 위해 아래 기능을 적용했다.

### 구현됨

| 기능 | 설명 |
|------|------|
| **Query Rewriting / Domain Expansion** | 한국어 물류 용어와 영어 도메인 키워드를 함께 사용해 검색 회수율을 높인다. |
| **Smart Snippet** | 검색 결과에서 쿼리와 관련 높은 본문 구간을 발췌한다. |
| **Entity Auto-Tag** | 본문과 메타데이터에서 Site, Vendor, Doc, Issue, Ref 등을 추출한다. |
| **Similar Email Finder** | 이메일 상세 뷰에서 유사 이메일 TOP 5를 찾는다. |
| **Timeline Reconstruction** | Case 번호 기준으로 관련 이메일을 시간순 스레드로 보여준다. |
| **Search Result Summary** | 검색 결과 상위 10건을 Gemini로 일괄 요약한다. |
| **Issue Clustering** | 검색 결과의 이슈 유형을 자동 분류한다. |
| **Key Decision Finder** | 핵심 의사결정 이메일 TOP 10을 추린다. |
| **Natural Language Query** | 자연어 조건을 SQL 조건으로 변환해 이메일을 검색한다. |
| **Exact Identifier Search** | 번호·케이스·LPO·rowkey 식별자 검색을 BM25와 별도로 수행한다. |
| **RRF Search Copilot** | BM25, semantic, exact, field, entity 신호를 순위 기반으로 결합한다. |

### 유지할 개선 후보

| 기능 | 설명 |
|------|------|
| **Multi-turn Search** | "이전 결과에서 2025년 것만", "같은 발신자의 다른 이메일" 등 후속 질문으로 검색 범위 좁히기 |
| **Attachment Coverage Audit** | Google Drive PDF가 있는 메일과 DB `linkkey` 매핑 누락을 정기 점검한다. |
| **Mobile UX Regression Test** | 휴대폰 폭에서 검색, 본문 보기, PDF 열기 흐름을 자동 검증한다. |

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

### 모바일에서 PDF 열기

1. 검색 후 `본문 보기`에서 메일을 선택한다.
2. 본문 위에 `첨부 PDF 열기 (Google Drive)` 버튼이 있으면 Drive 뷰어로 연다.
3. Drive 뷰어가 모바일에서 열리지 않으면 `PDF 다운로드` 버튼을 누른다.
4. 메일에 정확히 연결된 PDF가 없으면 날짜별 첨부파일 폴더 링크가 표시된다.

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
drive_links.json        linkkey → Google Drive PDF 파일 ID 매핑
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
- `drive_links.json` — Google Drive PDF 첨부 연결용 매핑 파일
- `OUTLOOK_HVDC_*.xlsx` — gitignore 처리 (내부 민감 데이터)
- Streamlit Cloud 무료 티어: RAM 1 GB, 최초 시맨틱 검색 시 모델 로드 ~5초
- Anomaly Detection 기능은 v2.1에서 제거됨

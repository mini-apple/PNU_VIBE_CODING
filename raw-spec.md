# raw-spec.md — 취준생 뉴스 수집·요약 AI Agent
> 제약 조건: 하루 바이브코딩으로 완성 / gpt-5-mini / RAG only

---

## 1. 프로젝트 개요

취업 준비생을 위한 뉴스 수집·요약 AI Agent.
**두 가지 핵심 기능**을 탭으로 분리하여 제공한다.

| 기능 | 설명 |
|------|------|
| **① 채용 뉴스** | 사용자 분야·기업 기반 맞춤 채용 공고 및 업계 동향 수집·요약 |
| **② 경제 뉴스** | 국내외 전반적인 경제 뉴스 수집·요약 |

두 기능 모두 각 뉴스에 **원문 링크**를 포함하여 클릭 시 원문으로 이동한다.

---

## 2. 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                         Streamlit UI                            │
│                                                                 │
│  [사이드바]               [메인 — 탭 2개]                       │
│  · 취준 분야 선택          TAB 1: 채용 뉴스                     │
│  · 관심 기업 입력              분야·기업 맞춤 뉴스 리포트       │
│  · 경력 수준 선택              원문 링크 포함                   │
│                           TAB 2: 경제 뉴스                     │
│                               전반 경제 뉴스 요약 리포트        │
│                               원문 링크 포함                   │
└──────────┬───────────────────────────┬───────────────────────────┘
           │                           │
    build_job_queries()         ECONOMY_QUERIES (고정)
           │                           │
┌──────────▼───────────────────────────▼───────────────────────────┐
│                      LangChain AgentExecutor                     │
│                                                                  │
│  search_news → store_to_vectordb → query_vectordb                │
│  → generate_job_report  /  generate_economy_report              │
└──────────┬───────────────────────────────────────────────────────┘
           │
  ┌────────▼────────┐        ┌─────────────────────────────────┐
  │  Search Router  │        │           ChromaDB              │
  │  Tavily (우선)  │        │  collection: "job_news"         │
  │  DuckDuckGo     │        │  collection: "economy_news"     │
  │  (fallback)     │        │  메타데이터: url, title, source  │
  └─────────────────┘        └─────────────────────────────────┘
```

---

## 3. 기술 스택

| 레이어 | 기술 | 비고 |
|--------|------|------|
| UI | Streamlit | 사이드바 프로필 + 탭 2개 |
| LLM | **gpt-5-mini** | OpenAI API |
| Embedding | text-embedding-3-small | OpenAI API |
| Agent | LangChain AgentExecutor | OpenAI Functions 방식 |
| Output | PydanticOutputParser + OutputFixingParser | 스키마 강제 |
| VectorDB | ChromaDB | collection 2개 분리 운영 |
| 검색 | Tavily → DuckDuckGo fallback | |
| RAG | VectorStoreRetriever (Top-K 코사인 유사도) | |
| 청크 | RecursiveCharacterTextSplitter | chunk_size=500, overlap=50 |

---

## 4. 사용자 프로필 (사이드바)

```python
class UserProfile(BaseModel):
    field: str               # 취준 분야 (예: "백엔드 개발")
    companies: list[str]     # 관심 기업 (예: ["네이버", "카카오"])
    level: Literal["신입", "인턴", "경력 1-3년"]
    extra_keywords: list[str] = []   # 추가 키워드 (선택)
```

### 분야 프리셋 (selectbox)
백엔드 개발 / 프론트엔드 개발 / 데이터 분석 / AI·ML 엔지니어 / 서비스 기획·PM / UX 디자인 / 기타(직접 입력)

---

## 5. Pydantic 스키마

```python
from pydantic import BaseModel
from typing import Optional, Literal

# ── 공통 ──────────────────────────────────────────
class NewsArticle(BaseModel):
    """리포트 섹션 안에 들어가는 개별 기사 (링크 포함)"""
    title: str
    url: str                   # 원문 링크 (필수)
    source: str                # 출처 언론사
    one_line_summary: str      # 한 줄 요약

class NewsItem(BaseModel):
    """검색 결과 원본 저장용"""
    title: str
    url: str                   # 원문 링크 (필수)
    source: str
    published_date: Optional[str] = None
    summary: str
    keywords: list[str]

# ── 기능 ① 채용 뉴스 ─────────────────────────────
class JobReportSection(BaseModel):
    section_title: str         # 예: "채용 공고", "업계 동향"
    content: str               # 섹션 요약 본문
    articles: list[NewsArticle]  # 근거 기사 (링크 포함)

class JobReport(BaseModel):
    report_date: str
    target_field: str          # 취준 분야
    target_companies: list[str]
    headline_summary: str      # 3줄 이내 핵심 요약
    sections: list[JobReportSection]
    action_items: list[str]    # 예: "네이버 공채 마감 D-3"
    total_articles_analyzed: int

# ── 기능 ② 경제 뉴스 ─────────────────────────────
class EconomyReportSection(BaseModel):
    section_title: str         # 예: "국내 경제", "글로벌 시장", "산업 동향"
    content: str
    articles: list[NewsArticle]  # 근거 기사 (링크 포함)

class EconomyReport(BaseModel):
    report_date: str
    headline_summary: str      # 3줄 이내 핵심 요약
    sections: list[EconomyReportSection]
    key_indicators: list[str]  # 예: "코스피 -1.2%", "원/달러 1,380원"
    total_articles_analyzed: int
```

---

## 6. 검색 쿼리 전략

### 기능 ① 채용 뉴스 — 동적 쿼리 (query_builder.py)
```python
# 분야 프리셋 쿼리
FIELD_PRESET_QUERIES = {
    "백엔드 개발":    ["백엔드 개발자 채용 공고", "서버 개발 트렌드"],
    "프론트엔드 개발": ["프론트엔드 개발자 채용 공고", "React Next.js 트렌드"],
    "데이터 분석":    ["데이터 분석가 채용 공고", "데이터 사이언티스트 공채"],
    "AI·ML 엔지니어": ["AI 엔지니어 채용 공고", "LLM MLOps 채용"],
    "서비스 기획·PM": ["서비스 기획자 채용 공고", "PM 프로덕트 매니저 공채"],
    "UX 디자인":      ["UX 디자이너 채용 공고", "UI 디자인 트렌드"],
}

def build_job_queries(profile: UserProfile) -> list[str]:
    queries = list(FIELD_PRESET_QUERIES.get(profile.field, [profile.field + " 채용"]))
    for company in profile.companies:
        queries.append(f"{company} {profile.field} 채용")
    queries += profile.extra_keywords
    return queries
```

### 기능 ② 경제 뉴스 — 고정 쿼리 (constants.py)
```python
ECONOMY_QUERIES = [
    "오늘 국내 경제 뉴스",
    "코스피 코스닥 증시 동향",
    "원달러 환율 오늘",
    "글로벌 경제 뉴스 오늘",
    "금리 인플레이션 최신 동향",
    "국내 주요 기업 실적 뉴스",
]
```

---

## 7. Tool 목록 (agent/tools.py)

```python
@tool
def search_news(queries_json: str, collection_name: str,
                max_results_per_query: int = 5) -> str:
    """
    쿼리 리스트로 검색 실행 (Tavily → DuckDuckGo fallback).
    collection_name: "job_news" | "economy_news"
    반환: NewsItem 리스트 JSON (url 필수 포함)
    """

@tool
def store_articles_to_vectordb(articles_json: str, collection_name: str) -> str:
    """
    청크 분할 후 지정 ChromaDB collection에 저장.
    메타데이터: url, title, source, published_date
    id = hash(url) → 중복 자동 방지
    반환: 저장된 청크 수
    """

@tool
def query_vectordb(query: str, collection_name: str, k: int = 5) -> str:
    """
    지정 collection에서 코사인 유사도 Top-K 검색.
    반환: 청크 본문 + 메타데이터(url, title, source) JSON
    """

@tool
def generate_job_report(field: str, companies_json: str, docs_json: str) -> str:
    """
    채용 뉴스 문서 기반 JobReport 생성.
    PydanticOutputParser 사용. NewsArticle에 url 포함.
    """

@tool
def generate_economy_report(docs_json: str) -> str:
    """
    경제 뉴스 문서 기반 EconomyReport 생성.
    PydanticOutputParser 사용. NewsArticle에 url 포함.
    """
```

---

## 8. 링크 저장 및 렌더링 전략

### 8.1 ChromaDB 메타데이터 저장
```python
# rag/vectorstore.py
collection.upsert(
    ids=[hashlib.md5(url.encode()).hexdigest()],  # url 기반 중복 방지
    documents=[chunk_text],
    metadatas=[{
        "url":            article.url,       # 원문 링크 — 핵심
        "title":          article.title,
        "source":         article.source,
        "published_date": article.published_date or "",
    }]
)
# query 결과의 metadatas["url"]을 리포트까지 그대로 전달
```

### 8.2 Streamlit 렌더링 (링크 클릭 가능)
```python
# app.py
def render_articles(articles: list[NewsArticle]):
    for a in articles:
        st.markdown(f"- **[{a.title}]({a.url})** ({a.source})")
        st.caption(a.one_line_summary)

# TAB 1 — 채용 뉴스
def render_job_report(report: JobReport):
    st.info(report.headline_summary)
    for section in report.sections:
        with st.expander(f"📌 {section.section_title}", expanded=True):
            st.markdown(section.content)
            render_articles(section.articles)
    st.markdown("### ✅ Action Items")
    for item in report.action_items:
        st.markdown(f"- {item}")

# TAB 2 — 경제 뉴스
def render_economy_report(report: EconomyReport):
    st.info(report.headline_summary)
    cols = st.columns(len(report.key_indicators))
    for col, indicator in zip(cols, report.key_indicators):
        col.metric(label="", value=indicator)
    for section in report.sections:
        with st.expander(f"📌 {section.section_title}", expanded=True):
            st.markdown(section.content)
            render_articles(section.articles)
```

---

## 9. 핵심 플로우

### 기능 ① 채용 뉴스
```
사이드바 입력: 분야="백엔드 개발", 기업=["네이버","카카오"], 레벨="신입"
       │
       ▼
build_job_queries(profile)
  → ["네이버 백엔드 채용", "카카오 백엔드 채용", "백엔드 개발자 채용 공고", ...]
       │
       ▼
AgentExecutor (collection="job_news")
  Step 1: search_news(queries_json, "job_news")
  Step 2: store_articles_to_vectordb(articles_json, "job_news")
  Step 3: query_vectordb("백엔드 개발 채용", "job_news", k=5)
  Step 4: generate_job_report(field, companies, docs_json)
       │
       ▼
render_job_report(report)  ← 섹션별 요약 + 클릭 가능 링크
```

### 기능 ② 경제 뉴스
```
TAB 2 진입 (프로필 무관, 고정 쿼리)
       │
       ▼
ECONOMY_QUERIES (고정 리스트)
       │
       ▼
AgentExecutor (collection="economy_news")
  Step 1: search_news(economy_queries_json, "economy_news")
  Step 2: store_articles_to_vectordb(articles_json, "economy_news")
  Step 3: query_vectordb("경제 뉴스 오늘", "economy_news", k=5)
  Step 4: generate_economy_report(docs_json)
       │
       ▼
render_economy_report(report)  ← 지표 metric + 섹션 + 클릭 가능 링크
```

---

## 10. 디렉터리 구조

```
news-agent/
├── app.py                      # Streamlit 진입점 (탭 2개)
├── constants.py                # ECONOMY_QUERIES, FIELD_PRESET_QUERIES
├── .env
├── requirements.txt
│
├── agent/
│   ├── executor.py             # AgentExecutor 초기화
│   ├── tools.py                # @tool 5개
│   └── prompts.py              # system prompt (job / economy 구분)
│
├── rag/
│   ├── vectorstore.py          # ChromaDB — collection 2개 관리
│   └── embedder.py             # OpenAIEmbeddings 래퍼
│
├── search/
│   ├── tavily_search.py
│   ├── duckduckgo_search.py
│   ├── router.py               # fallback 로직
│   └── query_builder.py        # build_job_queries(UserProfile)
│
├── schemas/
│   └── models.py               # UserProfile, NewsItem, JobReport, EconomyReport
│
├── report/
│   ├── job_generator.py        # JobReport PydanticOutputParser
│   └── economy_generator.py    # EconomyReport PydanticOutputParser
│
└── data/
    └── chroma_db/
        ├── job_news/           # 채용 뉴스 collection
        └── economy_news/       # 경제 뉴스 collection
```

---

## 11. 환경 설정

### requirements.txt
```
streamlit
langchain
langchain-openai
langchain-community
chromadb
pydantic
duckduckgo-search
tavily-python
python-dotenv
```

### .env
```
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...
LLM_MODEL=gpt-5-mini
EMBEDDING_MODEL=text-embedding-3-small
CHROMA_PERSIST_DIR=./data/chroma_db
RAG_TOP_K=5
MAX_RESULTS_PER_QUERY=5
```

---

## 12. 하루 바이브코딩 Task 순서

```
[오전 — 공통 기반]
□ 01. 프로젝트 폴더 + .env + requirements 설치
□ 02. schemas/models.py — UserProfile, NewsItem, NewsArticle,
                           JobReport, EconomyReport
□ 03. constants.py — ECONOMY_QUERIES, FIELD_PRESET_QUERIES
□ 04. search/query_builder.py — build_job_queries()
□ 05. search/tavily + duckduckgo + router.py
□ 06. 검색 단독 테스트 (쿼리 → 결과 출력 확인)

[오후 1 — RAG + 리포트 생성]
□ 07. rag/embedder.py + vectorstore.py (collection 2개, url 메타 포함)
□ 08. report/job_generator.py — PydanticOutputParser → JobReport
□ 09. report/economy_generator.py — PydanticOutputParser → EconomyReport

[오후 2 — Agent 조립]
□ 10. agent/tools.py — @tool 5개
□ 11. agent/prompts.py + executor.py
□ 12. Agent 단독 테스트 — 채용/경제 각각 JSON 출력 확인

[저녁 — UI 연결]
□ 13. app.py — 사이드바 + TAB 1(채용) + TAB 2(경제)
□ 14. render_job_report + render_economy_report (링크 렌더링)
□ 15. E2E 테스트 — 양쪽 탭 클릭, 링크 원문 이동 확인
□ 16. 버그 수정 + README.md
```

---

## 13. 주요 기술 결정

### 두 기능을 탭으로 분리하는 이유
채용 뉴스와 경제 뉴스는 쿼리 생성 방식, 리포트 스키마, ChromaDB collection이 모두 다르다.
하나의 Agent에 모두 넣으면 Tool 선택 로직이 복잡해지고 디버깅이 어렵다.
탭으로 분리하면 각 탭이 독립적인 Agent 호출을 트리거하므로 흐름이 단순해진다.

### ChromaDB collection을 2개로 분리하는 이유
채용 뉴스와 경제 뉴스를 같은 collection에 넣으면 RAG 검색 시 서로 다른 도메인의 청크가 섞여 검색 품질이 떨어진다.
collection을 분리하면 각 기능이 자기 도메인 청크만 검색하므로 정밀도가 높아진다.

### 경제 뉴스 쿼리를 고정하는 이유
경제 뉴스는 사용자 프로필과 무관하게 동일한 주제(증시, 환율, 금리, 실적)를 다룬다.
LLM에게 쿼리 생성을 맡기면 매 실행마다 결과가 달라진다.
고정 쿼리로 안정적인 수집 범위를 보장하고, 개발 시간도 절약한다.

### NewsArticle.url을 독립 필드로 두는 이유
LLM이 생성하는 `content` 본문 안에 url을 인라인으로 넣으면 PydanticOutputParser가 파싱하기 어렵다.
독립 필드로 분리하면 Streamlit에서 `[title](url)` 패턴으로 클릭 가능한 링크를 안정적으로 렌더링할 수 있다.

---

*버전: v0.5.0 | 작성일: 2026-04-04*

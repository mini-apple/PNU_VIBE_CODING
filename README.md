# 뉴스 수집 AI Agent

취업 준비생을 위한 Streamlit 기반 뉴스 수집·요약 AI Agent.

| 탭 | 기능 |
|----|------|
| 📌 분야 뉴스 | 지원 분야 산업 트렌드·기술 동향 뉴스 수집·요약 (원문 링크 포함) |
| 💹 경제 뉴스 | 국내외 전반 경제 뉴스 수집·요약 (증시·환율·금리 지표 포함) |

## 아키텍처

```
Streamlit UI
  └── 사이드바: 분야 / 관심 기업 / 경력 수준 / 추가 키워드 설정
  └── "뉴스 수집 시작" 버튼 → AgentExecutor 트리거

AgentExecutor (LangChain, gpt-5-mini)
  1. search_news        : Tavily → DuckDuckGo fallback
  2. store_to_vectordb  : ChromaDB 인메모리 (chunk_size=500)
  3. query_vectordb     : 코사인 유사도 Top-K 검색
  4. generate_report    : PydanticOutputParser + OutputFixingParser
```

## 빠른 시작

### 1. 환경 설정

```bash
cp .env.example .env
# .env 파일에 API 키를 입력하세요
```

`.env` 필수 항목:

| 키 | 설명 |
|----|------|
| `OPENAI_API_KEY` | OpenAI API 키 |
| `TAVILY_API_KEY` | Tavily Search API 키 (https://tavily.com) |
| `LLM_MODEL` | 사용할 LLM 모델명 (기본값: `gpt-5-mini`) |
| `EMBEDDING_MODEL` | 임베딩 모델명 (기본값: `text-embedding-3-small`) |

### 2. 패키지 설치

```bash
pip install -r requirements.txt
```

### 3. 실행

```bash
streamlit run app.py
```

브라우저에서 `http://localhost:8501` 접속

## 디렉터리 구조

```
news-collector/
├── app.py              # Streamlit 진입점
├── constants.py        # 쿼리 프리셋, 선택지 상수
├── requirements.txt
├── .env.example
│
├── agent/
│   ├── executor.py     # AgentExecutor 팩토리 + 실행
│   ├── tools.py        # @tool 5개 (search / store / query / generate)
│   └── prompts.py      # 시스템 프롬프트
│
├── rag/
│   ├── embedder.py     # OpenAIEmbeddings 래퍼
│   └── vectorstore.py  # ChromaDB 인메모리 클라이언트
│
├── report/
│   ├── field_generator.py    # FieldNewsReport 생성
│   └── economy_generator.py  # EconomyReport 생성
│
├── schemas/
│   └── models.py       # Pydantic 스키마
│
└── search/
    ├── tavily_search.py
    ├── duckduckgo_search.py
    ├── router.py         # Tavily → DuckDuckGo fallback
    └── query_builder.py  # 분야별 쿼리 생성
```

## 주요 기술 결정

- **ChromaDB 인메모리**: 앱 재시작 시 초기화 → 항상 최신 뉴스 보장
- **AgentExecutor**: 순차 파이프라인을 기본으로 하되 동적 재검색 유연성 확보
- **PydanticOutputParser + OutputFixingParser**: LLM 출력 스키마 강제 및 자동 수정
- **Tavily → DuckDuckGo fallback**: API 장애 시 자동 전환으로 가용성 확보

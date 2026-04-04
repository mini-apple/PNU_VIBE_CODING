import json
import logging

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
def search_news(
    queries_json: str,
    collection_name: str,
    max_results_per_query: int = 5,
) -> str:
    """
    쿼리 리스트로 뉴스를 검색합니다 (Tavily → DuckDuckGo fallback).

    Args:
        queries_json: JSON 배열 형식의 검색 쿼리 목록. 예: '["AI 뉴스", "LLM 동향"]'
        collection_name: 저장할 컬렉션 이름 ("field_news" 또는 "economy_news")
        max_results_per_query: 쿼리당 최대 결과 수 (기본값 5)

    Returns:
        NewsItem 리스트 JSON 문자열 (url 필수 포함)
    """
    from search.router import search_with_fallback

    try:
        queries: list[str] = json.loads(queries_json)
    except json.JSONDecodeError:
        queries = [queries_json]

    all_articles: list[dict] = []
    seen_urls: set[str] = set()

    for query in queries:
        results = search_with_fallback(query, max_results_per_query)
        for r in results:
            url = r.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                all_articles.append(
                    {
                        "title": r.get("title", ""),
                        "url": url,
                        "source": r.get("source", url.split("/")[2] if url else "unknown"),
                        "published_date": r.get("published_date"),
                        "summary": r.get("content", ""),
                        "keywords": [],
                    }
                )

    logger.info("search_news: 총 %d건 수집 (collection=%s)", len(all_articles), collection_name)
    return json.dumps(all_articles, ensure_ascii=False)


@tool
def store_articles_to_vectordb(articles_json: str, collection_name: str) -> str:
    """
    기사 목록을 청크 분할 후 ChromaDB 컬렉션에 저장합니다.

    Args:
        articles_json: search_news 반환값 (NewsItem 리스트 JSON)
        collection_name: 저장할 컬렉션 이름 ("field_news" 또는 "economy_news")

    Returns:
        저장된 청크 수 (문자열)
    """
    from rag.vectorstore import upsert_articles
    from rag.embedder import embed_text

    try:
        articles_data: list[dict] = json.loads(articles_json)
    except json.JSONDecodeError:
        return "0"

    if not articles_data:
        return "0"

    count = upsert_articles(articles_data, collection_name, embed_text)
    return str(count)


@tool
def query_vectordb(query: str, collection_name: str, k: int = 5) -> str:
    """
    ChromaDB 컬렉션에서 코사인 유사도 Top-K 청크를 검색합니다.

    Args:
        query: 검색 쿼리 문자열
        collection_name: 검색할 컬렉션 이름 ("field_news" 또는 "economy_news")
        k: 반환할 결과 수 (기본값 5)

    Returns:
        청크 본문 + 메타데이터(url, title, source) JSON 문자열
    """
    from rag.vectorstore import query_collection
    from rag.embedder import embed_text

    docs = query_collection(query, collection_name, k, embed_text)
    return json.dumps(docs, ensure_ascii=False)


@tool
def generate_field_report(field: str, companies_json: str, docs_json: str) -> str:
    """
    분야 뉴스 문서를 기반으로 FieldNewsReport를 생성합니다.

    Args:
        field: 지원 분야 (예: "반도체", "AI·ML 엔지니어")
        companies_json: 관심 기업 JSON 배열 (예: '["삼성전자", "SK하이닉스"]')
        docs_json: query_vectordb 반환값

    Returns:
        FieldNewsReport JSON 문자열
    """
    from report.field_generator import generate_field_news_report

    try:
        companies: list[str] = json.loads(companies_json)
    except json.JSONDecodeError:
        companies = []

    try:
        docs: list[dict] = json.loads(docs_json)
    except json.JSONDecodeError:
        docs = []

    report = generate_field_news_report(field, companies, docs)
    return report.model_dump_json()


@tool
def generate_economy_report(docs_json: str) -> str:
    """
    경제 뉴스 문서를 기반으로 EconomyReport를 생성합니다.

    Args:
        docs_json: query_vectordb 반환값

    Returns:
        EconomyReport JSON 문자열
    """
    from report.economy_generator import generate_economy_news_report

    try:
        docs: list[dict] = json.loads(docs_json)
    except json.JSONDecodeError:
        docs = []

    report = generate_economy_news_report(docs)
    return report.model_dump_json()

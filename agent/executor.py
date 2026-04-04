from __future__ import annotations

import json
import logging

from constants import ECONOMY_QUERIES
from rag.embedder import embed_text
from rag.vectorstore import upsert_articles, query_collection
from report.economy_generator import generate_economy_news_report
from report.field_generator import generate_field_news_report
from schemas.models import FieldNewsReport, EconomyReport, UserProfile
from search.query_builder import build_field_queries
from search.router import search_with_fallback

logger = logging.getLogger(__name__)

RAG_TOP_K = 5
MAX_RESULTS_PER_QUERY = 5


def _collect_articles(queries: list[str], collection_name: str) -> list[dict]:
    """쿼리 목록으로 뉴스를 검색하고 ChromaDB에 저장 후 기사 목록을 반환합니다."""
    all_articles: list[dict] = []
    seen_urls: set[str] = set()

    for query in queries:
        results = search_with_fallback(query, MAX_RESULTS_PER_QUERY)
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

    logger.info("[%s] 검색 완료: %d건", collection_name, len(all_articles))

    if all_articles:
        chunk_count = upsert_articles(all_articles, collection_name, embed_text)
        logger.info("[%s] ChromaDB 저장: %d chunks", collection_name, chunk_count)
    else:
        logger.warning("[%s] 검색 결과 없음 — 쿼리: %s", collection_name, queries)

    return all_articles


def _retrieve_docs(query: str, collection_name: str) -> list[dict]:
    """ChromaDB에서 관련 청크를 검색합니다."""
    docs = query_collection(query, collection_name, RAG_TOP_K, embed_text)
    logger.info("[%s] RAG 검색 결과: %d chunks", collection_name, len(docs))
    return docs


def run_field_agent(profile: UserProfile) -> FieldNewsReport:
    """
    분야 뉴스 파이프라인을 실행합니다.
    Search → Store → RAG Query → LLM Report 순으로 직접 실행합니다.
    """
    queries = build_field_queries(profile)
    logger.info("분야 뉴스 쿼리 (%d개): %s", len(queries), queries)

    # Step 1 & 2: 검색 + ChromaDB 저장
    _collect_articles(queries, "field_news")

    # Step 3: RAG 검색
    rag_query = f"{profile.field} 최신 기술 동향 산업 트렌드"
    docs = _retrieve_docs(rag_query, "field_news")

    # Step 4: LLM 리포트 생성
    return generate_field_news_report(profile.field, profile.companies, docs)


def run_economy_agent() -> EconomyReport:
    """
    경제 뉴스 파이프라인을 실행합니다.
    Search → Store → RAG Query → LLM Report 순으로 직접 실행합니다.
    """
    logger.info("경제 뉴스 쿼리 (%d개): %s", len(ECONOMY_QUERIES), ECONOMY_QUERIES)

    # Step 1 & 2: 검색 + ChromaDB 저장
    _collect_articles(ECONOMY_QUERIES, "economy_news")

    # Step 3: RAG 검색
    docs = _retrieve_docs("오늘 주요 경제 동향 증시 환율 금리", "economy_news")

    # Step 4: LLM 리포트 생성
    return generate_economy_news_report(docs)

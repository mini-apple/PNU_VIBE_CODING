import logging

from search.tavily_search import search_tavily
from search.duckduckgo_search import search_duckduckgo

logger = logging.getLogger(__name__)


def search_with_fallback(query: str, max_results: int = 5) -> list[dict]:
    """Tavily로 검색 후 실패 시 DuckDuckGo로 자동 전환합니다."""
    try:
        results = search_tavily(query, max_results)
        if results:
            logger.info("Tavily 검색 성공: %s (%d건)", query, len(results))
            return results
        logger.warning("Tavily 결과 없음, DuckDuckGo로 전환: %s", query)
    except Exception as e:
        logger.warning("Tavily 검색 실패 (%s), DuckDuckGo로 전환: %s", e, query)

    try:
        results = search_duckduckgo(query, max_results)
        logger.info("DuckDuckGo 검색 성공: %s (%d건)", query, len(results))
        return results
    except Exception as e:
        logger.error("DuckDuckGo 검색 실패 (%s): %s", e, query)
        return []

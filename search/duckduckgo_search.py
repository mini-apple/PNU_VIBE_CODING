import logging
import time

logger = logging.getLogger(__name__)

_RETRY_COUNT = 2
_RETRY_DELAY = 2.0  # seconds


def search_duckduckgo(query: str, max_results: int = 5) -> list[dict]:
    """DuckDuckGo News 검색 API로 뉴스를 검색합니다 (API 키 불필요).

    ddgs.news() 우선 → 실패 시 ddgs.text() fallback.
    Rate limit 대응을 위해 최대 2회 재시도합니다.
    """
    from duckduckgo_search import DDGS
    from duckduckgo_search.exceptions import DuckDuckGoSearchException

    for attempt in range(_RETRY_COUNT + 1):
        try:
            with DDGS() as ddgs:
                # 뉴스 전용 검색 (날짜·출처 포함)
                try:
                    news_items = list(ddgs.news(query, max_results=max_results))
                except (DuckDuckGoSearchException, Exception) as e:
                    logger.debug("ddgs.news() 실패 (%s), text()로 전환", e)
                    news_items = []

                if news_items:
                    return [
                        {
                            "title": r.get("title", ""),
                            "url": r.get("url", ""),
                            "content": r.get("body", ""),
                            "source": r.get("source", ""),
                            "published_date": r.get("date", None),
                        }
                        for r in news_items
                    ]

                # 뉴스 결과 없으면 일반 웹 검색 fallback
                text_items = list(ddgs.text(query, max_results=max_results))
                return [
                    {
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "content": r.get("body", ""),
                        "source": r.get("href", "").split("/")[2] if r.get("href") else "unknown",
                        "published_date": None,
                    }
                    for r in text_items
                ]

        except Exception as e:
            if attempt < _RETRY_COUNT:
                logger.warning(
                    "DuckDuckGo 검색 실패 (시도 %d/%d): %s — %.1f초 후 재시도",
                    attempt + 1, _RETRY_COUNT + 1, e, _RETRY_DELAY,
                )
                time.sleep(_RETRY_DELAY)
            else:
                logger.error("DuckDuckGo 검색 최종 실패: %s | 쿼리: %s", e, query)

    return []

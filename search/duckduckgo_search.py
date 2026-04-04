def search_duckduckgo(query: str, max_results: int = 5) -> list[dict]:
    """DuckDuckGo News 검색 API로 뉴스를 검색합니다 (API 키 불필요).

    ddgs.news()를 우선 시도하고 결과가 없으면 ddgs.text()로 fallback합니다.
    """
    from duckduckgo_search import DDGS

    results: list[dict] = []

    with DDGS() as ddgs:
        # 뉴스 전용 검색 — 날짜·출처 포함
        try:
            news_items = list(ddgs.news(query, max_results=max_results))
        except Exception:
            news_items = []

        if news_items:
            for r in news_items:
                url = r.get("url", "")
                results.append(
                    {
                        "title": r.get("title", ""),
                        "url": url,
                        "content": r.get("body", ""),
                        "source": r.get("source", url.split("/")[2] if url else "unknown"),
                        "published_date": r.get("date", None),
                    }
                )
            return results

        # 뉴스 결과 없을 때 일반 웹 검색으로 fallback
        for r in ddgs.text(query, max_results=max_results):
            url = r.get("href", "")
            results.append(
                {
                    "title": r.get("title", ""),
                    "url": url,
                    "content": r.get("body", ""),
                    "source": url.split("/")[2] if url else "unknown",
                    "published_date": None,
                }
            )

    return results

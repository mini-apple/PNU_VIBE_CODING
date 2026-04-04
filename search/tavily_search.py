import os


def search_tavily(query: str, max_results: int = 5) -> list[dict]:
    """Tavily 검색 API로 뉴스를 검색합니다."""
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise ValueError("TAVILY_API_KEY 환경변수가 설정되지 않았습니다.")

    from tavily import TavilyClient

    client = TavilyClient(api_key=api_key)
    response = client.search(query=query, max_results=max_results, search_depth="basic")

    results = []
    for r in response.get("results", []):
        url = r.get("url", "")
        results.append(
            {
                "title": r.get("title", ""),
                "url": url,
                "content": r.get("content", ""),
                "source": url.split("/")[2] if url else "unknown",
                "published_date": r.get("published_date", None),
            }
        )
    return results

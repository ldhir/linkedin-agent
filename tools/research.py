from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional

from tavily import TavilyClient

from config import TAVILY_API_KEY

DEFAULT_QUERIES = [
    # Trending AI / tech topics
    "trending LinkedIn posts AI startups this week",
    "computer vision sports technology news",
    "consumer AI edtech funding news this week",
    "basketball technology AI coaching news",
    # Founder content inspiration
    "successful consumer app founders LinkedIn posts this week",
    "startup founders pre-seed seed Series A LinkedIn viral posts",
    "sports tech founders startup building in public LinkedIn",
    "up and coming startup founders raising funding 2026",
]


def _run_search(client: TavilyClient, query: str) -> dict:
    result = client.search(
        query=query,
        search_depth="advanced",
        max_results=5,
        topic="news",
        days=3,
        include_answer=True,
    )
    return {
        "query": query,
        "answer": result.get("answer"),
        "results": [
            {
                "title": r["title"],
                "url": r["url"],
                "content": r["content"][:500],
            }
            for r in result.get("results", [])
        ],
    }


def search_trending_topics(queries: Optional[List[str]] = None) -> List[dict]:
    client = TavilyClient(api_key=TAVILY_API_KEY)
    search_queries = queries or DEFAULT_QUERIES

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(_run_search, client, q) for q in search_queries]
        return [f.result() for f in futures]

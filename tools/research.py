import os
from typing import List, Optional

from tavily import TavilyClient

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


def search_trending_topics(queries: Optional[List[str]] = None) -> List[dict]:
    client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
    all_results = []

    for query in (queries or DEFAULT_QUERIES):
        result = client.search(
            query=query,
            search_depth="advanced",
            max_results=5,
            topic="news",
            days=3,
            include_answer=True,
        )
        all_results.append({
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
        })

    return all_results

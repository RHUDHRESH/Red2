from __future__ import annotations

from dataclasses import dataclass
from typing import List

try:
    from duckduckgo_search import DDGS
except Exception:  # pragma: no cover
    DDGS = None  # type: ignore


@dataclass
class NewsItem:
    title: str
    url: str
    date: str
    source: str
    snippet: str


class NewsService:
    """News search via DuckDuckGo news endpoint."""

    async def search(self, query: str, *, max_results: int = 20) -> List[NewsItem]:
        out: List[NewsItem] = []
        if DDGS is None:
            return out
        with DDGS() as ddgs:
            try:
                items = ddgs.news(query, max_results=max_results)
                for it in items or []:
                    out.append(
                        NewsItem(
                            title=it.get("title", ""),
                            url=it.get("url", ""),
                            date=it.get("date", ""),
                            source=it.get("source", ""),
                            snippet=it.get("body", ""),
                        )
                    )
            except Exception:
                pass
        return out[:max_results]


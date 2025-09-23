from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .search_service import SearchService


@dataclass
class StackOverflowItem:
    title: str
    url: str
    snippet: str


class StackOverflowService:
    """StackOverflow question/answer discovery via site search."""

    def __init__(self, search: SearchService) -> None:
        self._search = search

    async def search(self, query: str, *, max_results: int = 10) -> List[StackOverflowItem]:
        hits = await self._search.search(f"site:stackoverflow.com {query}", max_results=max_results)
        return [StackOverflowItem(title=h.title, url=h.url, snippet=h.snippet) for h in hits]


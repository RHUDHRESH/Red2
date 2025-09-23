from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .search_service import SearchService


@dataclass
class InstagramItem:
    title: str
    url: str
    snippet: str


class InstagramService:
    """Public Instagram page discovery via site search (no private API)."""

    def __init__(self, search: SearchService) -> None:
        self._search = search

    async def search(self, query: str, *, max_results: int = 8) -> List[InstagramItem]:
        hits = await self._search.search(f"site:instagram.com {query}", max_results=max_results)
        return [InstagramItem(title=h.title, url=h.url, snippet=h.snippet) for h in hits]


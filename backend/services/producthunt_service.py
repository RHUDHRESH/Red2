from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .search_service import SearchService


@dataclass
class ProductHuntItem:
    title: str
    url: str
    snippet: str


class ProductHuntService:
    """Product Hunt discovery via site search (public pages)."""

    def __init__(self, search: SearchService) -> None:
        self._search = search

    async def search(self, query: str, *, max_results: int = 8) -> List[ProductHuntItem]:
        hits = await self._search.search(f"site:producthunt.com {query}", max_results=max_results)
        return [ProductHuntItem(title=h.title, url=h.url, snippet=h.snippet) for h in hits]


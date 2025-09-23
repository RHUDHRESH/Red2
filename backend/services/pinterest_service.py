from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .search_service import SearchService


@dataclass
class PinterestItem:
    title: str
    url: str
    snippet: str


class PinterestService:
    """Pinterest discovery via site search."""

    def __init__(self, search: SearchService) -> None:
        self._search = search

    async def search(self, query: str, *, max_results: int = 8) -> List[PinterestItem]:
        hits = await self._search.search(f"site:pinterest.com {query}", max_results=max_results)
        return [PinterestItem(title=h.title, url=h.url, snippet=h.snippet) for h in hits]


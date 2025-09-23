from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .search_service import SearchService


@dataclass
class SubstackItem:
    title: str
    url: str
    snippet: str


class SubstackService:
    """Substack post discovery via site search."""

    def __init__(self, search: SearchService) -> None:
        self._search = search

    async def search(self, query: str, *, max_results: int = 10) -> List[SubstackItem]:
        hits = await self._search.search(f"site:substack.com {query}", max_results=max_results)
        return [SubstackItem(title=h.title, url=h.url, snippet=h.snippet) for h in hits]


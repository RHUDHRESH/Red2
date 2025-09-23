from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .search_service import SearchService


@dataclass
class FacebookItem:
    title: str
    url: str
    snippet: str


class FacebookService:
    """Public Facebook page discovery via site search (no Graph API)."""

    def __init__(self, search: SearchService) -> None:
        self._search = search

    async def search(self, query: str, *, max_results: int = 8) -> List[FacebookItem]:
        hits = await self._search.search(f"site:facebook.com {query}", max_results=max_results)
        return [FacebookItem(title=h.title, url=h.url, snippet=h.snippet) for h in hits]


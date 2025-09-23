from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .search_service import SearchService


@dataclass
class TikTokItem:
    title: str
    url: str
    snippet: str


class TikTokService:
    """TikTok public page discovery via site search (no private API)."""

    def __init__(self, search: SearchService) -> None:
        self._search = search

    async def search(self, query: str, *, max_results: int = 8) -> List[TikTokItem]:
        hits = await self._search.search(f"site:tiktok.com {query}", max_results=max_results)
        return [TikTokItem(title=h.title, url=h.url, snippet=h.snippet) for h in hits]


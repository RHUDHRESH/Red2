from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .search_service import SearchService


@dataclass
class ThreadsItem:
    title: str
    url: str
    snippet: str


class ThreadsService:
    """Instagram Threads discovery via site search (threads.net)."""

    def __init__(self, search: SearchService) -> None:
        self._search = search

    async def search(self, query: str, *, max_results: int = 8) -> List[ThreadsItem]:
        hits = await self._search.search(f"site:threads.net {query}", max_results=max_results)
        return [ThreadsItem(title=h.title, url=h.url, snippet=h.snippet) for h in hits]


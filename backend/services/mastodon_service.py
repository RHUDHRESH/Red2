from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .search_service import SearchService


@dataclass
class MastodonItem:
    title: str
    url: str
    snippet: str


class MastodonService:
    """Mastodon discovery via site search across common instances.

    You can override instances in your code by crafting queries.
    """

    DEFAULT_INSTANCES = [
        "mastodon.social",
        "hachyderm.io",
        "fosstodon.org",
        "mstdn.social",
    ]

    def __init__(self, search: SearchService) -> None:
        self._search = search

    async def search(self, query: str, *, max_results: int = 8, instances: List[str] | None = None) -> List[MastodonItem]:
        inst = instances or self.DEFAULT_INSTANCES
        combined: List[MastodonItem] = []
        per = max(1, max_results // max(1, len(inst)))
        for host in inst:
            hits = await self._search.search(f"site:{host} {query}", max_results=per)
            combined.extend(MastodonItem(title=h.title, url=h.url, snippet=h.snippet) for h in hits)
        return combined[:max_results]


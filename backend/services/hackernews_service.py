from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional

import httpx


logger = logging.getLogger(__name__)


@dataclass
class HNItem:
    id: int
    title: str
    url: Optional[str]
    score: int
    by: str
    time: int


class HackerNewsService:
    """Lightweight HN client via official Firebase API and Algolia search."""

    def __init__(self) -> None:
        self._base = "https://hacker-news.firebaseio.com/v0"

    async def _item(self, client: httpx.AsyncClient, item_id: int) -> Optional[HNItem]:
        try:
            r = await client.get(f"{self._base}/item/{item_id}.json")
            if r.status_code != 200:
                return None
            j = r.json() or {}
            return HNItem(
                id=j.get("id", item_id),
                title=j.get("title", ""),
                url=j.get("url"),
                score=int(j.get("score", 0)),
                by=j.get("by", ""),
                time=int(j.get("time", 0)),
            )
        except Exception:
            return None

    async def top_stories(self, *, limit: int = 20) -> List[HNItem]:
        import asyncio
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{self._base}/topstories.json")
                ids = (r.json() or [])[:limit]
                items = await asyncio.gather(*[self._item(client, x) for x in ids])
                return [i for i in items if i]
        except Exception as e:
            logger.warning(f"[hn] top_stories failed: {e}")
            return []

    async def search(self, query: str, *, limit: int = 20) -> List[HNItem]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(
                    "https://hn.algolia.com/api/v1/search",
                    params={"query": query, "tags": "story", "hitsPerPage": limit},
                )
                if r.status_code != 200:
                    return []
                hits = r.json().get("hits", [])
                out: List[HNItem] = []
                for h in hits:
                    out.append(
                        HNItem(
                            id=int(h.get("objectID", 0)),
                            title=h.get("title", ""),
                            url=h.get("url"),
                            score=int(h.get("points", 0)),
                            by=h.get("author", ""),
                            time=int(h.get("created_at_i", 0)),
                        )
                    )
                return out
        except Exception as e:
            logger.warning(f"[hn] search failed: {e}")
            return []

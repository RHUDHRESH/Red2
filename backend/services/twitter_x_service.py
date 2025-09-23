from __future__ import annotations

import os
import logging
from dataclasses import dataclass
from typing import List, Optional

import httpx

from .search_service import SearchService, SearchResult


logger = logging.getLogger(__name__)


@dataclass
class Tweet:
    id: str
    text: str
    author_id: Optional[str]
    created_at: Optional[str]
    url: str


def _tweet_url(tid: str, username: Optional[str] = None) -> str:
    if username:
        return f"https://twitter.com/{username}/status/{tid}"
    return f"https://twitter.com/i/web/status/{tid}"


class TwitterXService:
    """Twitter/X access via official API when TWITTER_BEARER_TOKEN is set.

    Falls back to DuckDuckGo search (site:twitter.com) if token is missing or calls fail.
    """

    def __init__(self, search: SearchService) -> None:
        self._search = search
        self._token = os.getenv("TWITTER_BEARER_TOKEN") or os.getenv("X_BEARER_TOKEN")
        self._base = "https://api.twitter.com/2"

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._token}"} if self._token else {}

    async def _get(self, path: str, params: dict) -> Optional[dict]:
        if not self._token:
            return None
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                r = await client.get(f"{self._base}{path}", headers=self._headers(), params=params)
                if r.status_code != 200:
                    logger.warning(f"[twitter] HTTP {r.status_code}: {r.text[:200]}")
                    return None
                return r.json()
        except Exception as e:
            logger.warning(f"[twitter] request failed: {e}")
            return None

    async def user_by_username(self, username: str) -> Optional[dict]:
        data = await self._get(f"/users/by/username/{username}", params={"user.fields": "name,username,created_at,description"})
        if data and data.get("data"):
            return data["data"]
        return None

    async def recent_tweets_by_user(self, username: str, *, max_results: int = 10) -> List[Tweet]:
        if self._token:
            user = await self.user_by_username(username)
            if user:
                uid = user.get("id")
                data = await self._get(f"/users/{uid}/tweets", params={
                    "max_results": max(5, min(max_results, 100)),
                    "tweet.fields": "created_at,author_id"
                })
                if data and data.get("data"):
                    out: List[Tweet] = []
                    for t in data["data"]:
                        out.append(Tweet(
                            id=t["id"],
                            text=t.get("text", ""),
                            author_id=t.get("author_id"),
                            created_at=t.get("created_at"),
                            url=_tweet_url(t["id"], username),
                        ))
                    return out
        # Fallback: search via DuckDuckGo
        q = f"site:twitter.com {username}"
        hits = await self._search.search(q, max_results=max_results)
        return [Tweet(id="", text=h.snippet, author_id=None, created_at=None, url=h.url) for h in hits]

    async def search_recent(self, query: str, *, max_results: int = 10) -> List[Tweet]:
        if self._token:
            data = await self._get("/tweets/search/recent", params={
                "query": query,
                "max_results": max(10, min(max_results, 100)),
                "tweet.fields": "created_at,author_id"
            })
            if data and data.get("data"):
                out: List[Tweet] = []
                for t in data["data"]:
                    out.append(Tweet(
                        id=t["id"],
                        text=t.get("text", ""),
                        author_id=t.get("author_id"),
                        created_at=t.get("created_at"),
                        url=_tweet_url(t["id"]),
                    ))
                return out
        # Fallback: DuckDuckGo site search
        hits = await self._search.search(f"site:twitter.com {query}", max_results=max_results)
        return [Tweet(id="", text=h.snippet, author_id=None, created_at=None, url=h.url) for h in hits]


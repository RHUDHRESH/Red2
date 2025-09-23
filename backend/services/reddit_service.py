from __future__ import annotations

import os
import logging
from dataclasses import dataclass
from typing import List, Optional

from .search_service import SearchService

logger = logging.getLogger(__name__)

try:
    import praw  # type: ignore
except Exception:  # pragma: no cover
    praw = None  # type: ignore


@dataclass
class RedditPost:
    title: str
    url: str
    author: Optional[str]
    score: int
    created_utc: Optional[float]
    subreddit: Optional[str]
    comments_url: Optional[str]


class RedditService:
    """Reddit helper using PRAW when credentials are set; otherwise site search fallback.

    Env vars (optional): REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT
    """

    def __init__(self, search: SearchService) -> None:
        self._search = search
        self._reddit = None
        if praw is not None:
            cid = os.getenv("REDDIT_CLIENT_ID")
            csec = os.getenv("REDDIT_CLIENT_SECRET")
            ua = os.getenv("REDDIT_USER_AGENT") or "geo-strategist/1.0"
            if cid and csec:
                try:
                    self._reddit = praw.Reddit(client_id=cid, client_secret=csec, user_agent=ua)
                except Exception as e:
                    logger.warning(f"[reddit] failed to init PRAW: {e}")

    async def top_posts(self, subreddit: str, *, time_filter: str = "day", limit: int = 10) -> List[RedditPost]:
        if self._reddit is not None:
            try:
                sub = self._reddit.subreddit(subreddit)
                out: List[RedditPost] = []
                for s in sub.top(time_filter=time_filter, limit=limit):  # type: ignore[attr-defined]
                    out.append(RedditPost(
                        title=getattr(s, "title", ""),
                        url=f"https://www.reddit.com{s.permalink}" if getattr(s, "permalink", None) else getattr(s, "url", ""),
                        author=str(getattr(s, "author", "")) if getattr(s, "author", None) else None,
                        score=int(getattr(s, "score", 0)),
                        created_utc=float(getattr(s, "created_utc", 0.0)),
                        subreddit=str(getattr(s, "subreddit", subreddit)),
                        comments_url=f"https://www.reddit.com{s.permalink}" if getattr(s, "permalink", None) else None,
                    ))
                return out
            except Exception as e:
                logger.warning(f"[reddit] top_posts failed, fallback to site search: {e}")
        # Fallback via DuckDuckGo
        hits = await self._search.search(f"site:reddit.com/r/{subreddit}", max_results=limit)
        return [RedditPost(title=h.title, url=h.url, author=None, score=0, created_utc=None, subreddit=subreddit, comments_url=h.url) for h in hits]

    async def search_subreddit(self, subreddit: str, query: str, *, limit: int = 10) -> List[RedditPost]:
        if self._reddit is not None:
            try:
                sub = self._reddit.subreddit(subreddit)
                out: List[RedditPost] = []
                for s in sub.search(query, limit=limit):  # type: ignore[attr-defined]
                    out.append(RedditPost(
                        title=getattr(s, "title", ""),
                        url=f"https://www.reddit.com{s.permalink}" if getattr(s, "permalink", None) else getattr(s, "url", ""),
                        author=str(getattr(s, "author", "")) if getattr(s, "author", None) else None,
                        score=int(getattr(s, "score", 0)),
                        created_utc=float(getattr(s, "created_utc", 0.0)),
                        subreddit=str(getattr(s, "subreddit", subreddit)),
                        comments_url=f"https://www.reddit.com{s.permalink}" if getattr(s, "permalink", None) else None,
                    ))
                return out
            except Exception as e:
                logger.warning(f"[reddit] search_subreddit failed, fallback to site search: {e}")
        hits = await self._search.search(f"site:reddit.com/r/{subreddit} {query}", max_results=limit)
        return [RedditPost(title=h.title, url=h.url, author=None, score=0, created_utc=None, subreddit=subreddit, comments_url=h.url) for h in hits]

    async def search(self, query: str, *, limit: int = 10) -> List[RedditPost]:
        hits = await self._search.search(f"site:reddit.com {query}", max_results=limit)
        return [RedditPost(title=h.title, url=h.url, author=None, score=0, created_utc=None, subreddit=None, comments_url=h.url) for h in hits]


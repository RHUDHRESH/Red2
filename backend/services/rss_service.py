from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List

try:
    import feedparser
except Exception:  # pragma: no cover
    feedparser = None  # type: ignore


logger = logging.getLogger(__name__)


@dataclass
class FeedItem:
    title: str
    url: str
    summary: str
    published: str


class RSSService:
    """Parse RSS/Atom feeds and normalize entries."""

    async def parse(self, url: str) -> List[FeedItem]:
        if feedparser is None:
            logger.warning("feedparser not installed; RSSService disabled")
            return []
        try:
            fp = feedparser.parse(url)
            items: List[FeedItem] = []
            for e in fp.entries or []:
                link = getattr(e, "link", "")
                title = getattr(e, "title", "")
                summary = getattr(e, "summary", getattr(e, "description", ""))
                published = getattr(e, "published", getattr(e, "updated", ""))
                if link:
                    items.append(FeedItem(title=title, url=link, summary=summary, published=published))
            return items
        except Exception as e:
            logger.warning(f"[rss] parse failed for {url}: {e}")
            return []


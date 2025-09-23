from __future__ import annotations

from dataclasses import dataclass
from typing import List

try:
    from duckduckgo_search import DDGS
except Exception:  # pragma: no cover
    DDGS = None  # type: ignore


@dataclass
class VideoItem:
    title: str
    url: str
    source: str
    duration: str


class YouTubeSearchService:
    """Video search via DuckDuckGo; filters results to YouTube when possible."""

    async def search(self, query: str, *, max_results: int = 10) -> List[VideoItem]:
        out: List[VideoItem] = []
        if DDGS is None:
            return out
        with DDGS() as ddgs:
            try:
                # ddgs.videos may include multiple sources; we prefer youtube
                vids = ddgs.videos(query, max_results=max_results)
                for v in vids or []:
                    url = v.get("content") or v.get("url") or ""
                    title = v.get("title") or ""
                    source = v.get("source") or ""
                    duration = v.get("duration") or ""
                    if url:
                        out.append(VideoItem(title=title, url=url, source=source, duration=duration))
            except Exception:
                pass
        # Prefer YouTube links first
        out.sort(key=lambda x: ("youtube" not in x.url, x.title))
        return out[:max_results]


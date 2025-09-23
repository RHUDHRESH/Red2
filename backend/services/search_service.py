from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict

try:
    from duckduckgo_search import DDGS
except Exception:  # pragma: no cover
    DDGS = None  # type: ignore


logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str


class SearchService:
    """Lightweight web search via DuckDuckGo (no API key).

    Falls back gracefully if the package is unavailable.
    """

    def __init__(self) -> None:
        if DDGS is None:
            logger.warning("duckduckgo-search not installed; SearchService will be disabled.")
        self._cache: Dict[str, List[SearchResult]] = {}

    async def search(self, query: str, *, max_results: int = 8, region: str = "wt-wt", safesearch: str = "moderate") -> List[SearchResult]:
        if DDGS is None:
            return []
        key = f"{query}|{max_results}|{region}|{safesearch}"
        if key in self._cache:
            return self._cache[key][:]
        try:
            # duckduckgo_search is sync; run quickly without blocking heavy I/O
            with DDGS() as ddgs:
                results = ddgs.text(query, region=region, safesearch=safesearch, max_results=max_results)
            out: List[SearchResult] = []
            for item in results or []:
                url = item.get("href") or item.get("url") or ""
                title = item.get("title") or item.get("title_full") or ""
                snippet = item.get("body") or item.get("snippet") or ""
                if url:
                    out.append(SearchResult(title=title, url=url, snippet=snippet))
            # cache a copy (simple unbounded cache; acceptable for dev; replace with LRU/TTL if needed)
            self._cache[key] = out[:]
            return out
        except Exception as e:
            logger.error(f"[search] error during DDG query '{query}': {e}")
            return []

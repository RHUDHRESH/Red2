from __future__ import annotations

import asyncio
import logging
from urllib.parse import urlparse, urljoin
from typing import Dict, Set, List, Optional

from bs4 import BeautifulSoup

from .web_scraper_service import WebScraperService


logger = logging.getLogger(__name__)


class CrawlService:
    """Simple, domain-scoped crawler using the pooled scraper client.

    Not a full crawler; best-effort for small research tasks.
    """

    def __init__(self, scraper: WebScraperService) -> None:
        self._scraper = scraper

    async def crawl(self, seed_url: str, *, max_pages: int = 20, allowed_domains: Optional[List[str]] = None) -> Dict[str, str]:
        start = urlparse(seed_url)
        base_domain = start.netloc
        allowed: Set[str] = set(d.lower() for d in (allowed_domains or [base_domain]))

        seen: Set[str] = set()
        queue: List[str] = [seed_url]
        results: Dict[str, str] = {}
        sem = asyncio.Semaphore(6)

        async def fetch(url: str):
            async with sem:
                try:
                    resp = await self._scraper._client.get(url, timeout=8.0)  # type: ignore[attr-defined]
                    if resp.status_code != 200:
                        return url, ""
                    html = resp.text
                    text = self._scraper._extract_text(html)
                    return url, text
                except Exception:
                    return url, ""

        while queue and len(results) < max_pages:
            batch = []
            while queue and len(batch) < 6 and len(results) + len(batch) < max_pages:
                url = queue.pop(0)
                if url in seen:
                    continue
                seen.add(url)
                batch.append(url)

            if not batch:
                break
            fetched = await asyncio.gather(*(fetch(u) for u in batch))
            for url, text in fetched:
                if text:
                    results[url] = text

            # extract links from fetched pages
            for url, text in fetched:
                # to get links, we need HTML; we can refetch or skip. To avoid refetch, we only expand from text by reconstructing links is hard.
                # Small compromise: refetch HTML for link extraction for the first few pages.
                if len(results) >= max_pages:
                    break
                try:
                    resp = await self._scraper._client.get(url, timeout=6.0)  # type: ignore[attr-defined]
                    html = resp.text
                    soup = BeautifulSoup(html, "html.parser")
                    for a in soup.find_all("a", href=True):
                        href = a.get("href")
                        nxt = urljoin(url, href)
                        pu = urlparse(nxt)
                        if pu.scheme not in ("http", "https"):
                            continue
                        if pu.netloc.lower() not in allowed:
                            continue
                        if nxt not in seen:
                            queue.append(nxt)
                except Exception:
                    continue

        logger.info(f"[crawler] crawled {len(results)} pages from {seed_url}")
        return results


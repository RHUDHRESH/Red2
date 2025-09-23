
import asyncio
import logging
import httpx
from bs4 import BeautifulSoup


logger = logging.getLogger(__name__)


class WebScraperService:
    """
    Async web scraper with connection pooling, HTTP/2, and simple concurrency.
    Reuses a single AsyncClient for speed and lower overhead.
    """

    _DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        )
    }

    def __init__(self, *, timeout_s: float = 10.0, max_connections: int = 100, max_keepalive: int = 20, cache_size: int = 128) -> None:
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout_s),
            follow_redirects=True,
            http2=True,
            limits=httpx.Limits(max_connections=max_connections, max_keepalive_connections=max_keepalive),
            headers=self._DEFAULT_HEADERS.copy(),
        )
        self._cache: dict[str, str] = {}
        self._cache_size = cache_size

    async def close(self) -> None:
        await self._client.aclose()

    @staticmethod
    def _extract_text(html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        # Join stripped strings with a single space
        return " ".join(t.strip() for t in soup.stripped_strings)

    async def scrape_text(self, url: str) -> str:
        """Fetch and extract visible text from a single URL."""
        try:
            if url in self._cache:
                return self._cache[url]
            logger.info(f"[scraper] ▶ fetching: {url}")
            resp = await self._client.get(url)
            resp.raise_for_status()
            text = self._extract_text(resp.text)
            logger.info(f"[scraper] ✅ ok: {url} ({len(text)} chars)")
            # simple LRU-ish: trim when over size
            self._cache[url] = text
            if len(self._cache) > self._cache_size:
                # pop arbitrary oldest key (not exact LRU to keep light)
                first = next(iter(self._cache))
                self._cache.pop(first, None)
            return text
        except httpx.HTTPStatusError as e:
            logger.warning(f"[scraper] HTTP {e.response.status_code} for {url}")
            return ""
        except httpx.RequestError as e:
            logger.error(f"[scraper] error fetching {url}: {e}")
            return ""

    async def scrape_many(self, urls: list[str], *, concurrency: int = 8) -> dict[str, str]:
        """Fetch many URLs concurrently. Returns a map of url->text."""
        sem = asyncio.Semaphore(max(1, concurrency))

        async def _fetch(u: str) -> tuple[str, str]:
            async with sem:
                return u, await self.scrape_text(u)

        results = await asyncio.gather(*(_fetch(u) for u in urls), return_exceptions=False)
        return {u: txt for u, txt in results}

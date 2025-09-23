from __future__ import annotations

import httpx


class WikipediaService:
    """Simple Wikipedia search and summary via REST API."""

    BASE = "https://en.wikipedia.org/api/rest_v1"

    async def search(self, query: str, *, limit: int = 10):
        async with httpx.AsyncClient(timeout=4.0) as client:
            r = await client.get(f"{self.BASE}/page/summary/{query}")
            if r.status_code == 200:
                return [r.json()]
        # Fallback to opensearch-like endpoint
        async with httpx.AsyncClient(timeout=4.0) as client:
            r = await client.get(
                "https://en.wikipedia.org/w/rest.php/v1/search/title",
                params={"q": query, "limit": limit},
            )
            if r.status_code == 200:
                return r.json().get("pages", [])
        return []

    async def summary(self, title: str):
        async with httpx.AsyncClient(timeout=4.0) as client:
            r = await client.get(f"{self.BASE}/page/summary/{title}")
            if r.status_code == 200:
                return r.json()
        return None


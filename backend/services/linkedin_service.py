from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List

from .search_service import SearchService, SearchResult


logger = logging.getLogger(__name__)


@dataclass
class LinkedInItem:
    title: str
    url: str
    snippet: str


class LinkedInService:
    """LinkedIn helper via site search.

    LinkedIn's official API access is restricted; this service uses DuckDuckGo site search
    to find public profile/company/posts pages. For deeper integrations, use a compliant
    third-party provider (e.g., Apify actors) and add a credentialed client.
    """

    def __init__(self, search: SearchService) -> None:
        self._search = search

    async def search(self, query: str, *, max_results: int = 8) -> List[LinkedInItem]:
        hits = await self._search.search(f"site:linkedin.com {query}", max_results=max_results)
        return [LinkedInItem(title=h.title, url=h.url, snippet=h.snippet) for h in hits]

    async def find_company(self, company_name: str, *, max_results: int = 5) -> List[LinkedInItem]:
        q = f"site:linkedin.com/company {company_name}"
        hits = await self._search.search(q, max_results=max_results)
        return [LinkedInItem(title=h.title, url=h.url, snippet=h.snippet) for h in hits]

    async def find_people(self, name: str, *, location: str | None = None, max_results: int = 5) -> List[LinkedInItem]:
        q = f"site:linkedin.com/in {name}"
        if location:
            q += f" {location}"
        hits = await self._search.search(q, max_results=max_results)
        return [LinkedInItem(title=h.title, url=h.url, snippet=h.snippet) for h in hits]


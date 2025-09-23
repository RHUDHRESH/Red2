from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .twitter_x_service import TwitterXService, Tweet
from .linkedin_service import LinkedInService, LinkedInItem
from .search_service import SearchService


@dataclass
class SocialResults:
    tweets: List[Tweet]
    linkedin: List[LinkedInItem]


class SocialService:
    """Aggregator for social lookups across Twitter (X) and LinkedIn."""

    def __init__(self, search: SearchService) -> None:
        self.twitter = TwitterXService(search)
        self.linkedin = LinkedInService(search)

    async def quick_scan(self, topic: str, *, max_results: int = 6) -> SocialResults:
        tw = await self.twitter.search_recent(topic, max_results=max_results)
        li = await self.linkedin.search(topic, max_results=max_results)
        return SocialResults(tweets=tw, linkedin=li)


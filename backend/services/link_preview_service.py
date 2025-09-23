from __future__ import annotations

import logging
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from .web_scraper_service import WebScraperService


logger = logging.getLogger(__name__)


class LinkPreview:
    def __init__(self, url: str, title: str = "", description: str = "") -> None:
        self.url = url
        self.title = title
        self.description = description

    def to_dict(self):
        return {"url": self.url, "title": self.title, "description": self.description}


class LinkPreviewService:
    """Fetch basic metadata (title/description) for URLs with pooled client from scraper."""

    def __init__(self, scraper: WebScraperService) -> None:
        self._scraper = scraper

    async def fetch(self, url: str) -> LinkPreview:
        try:
            # Use scraper's pooled client
            resp = await self._scraper._client.get(url, timeout=5.0)  # type: ignore[attr-defined]
            resp.raise_for_status()
            html = resp.text
            soup = BeautifulSoup(html, "html.parser")
            title = ""
            if soup.title and soup.title.string:
                title = soup.title.string.strip()
            desc = ""
            tag = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
            if tag and tag.get("content"):
                desc = tag.get("content").strip()
            return LinkPreview(url, title, desc)
        except Exception as e:
            logger.warning(f"[linkpreview] failed for {url}: {e}")
            return LinkPreview(url)


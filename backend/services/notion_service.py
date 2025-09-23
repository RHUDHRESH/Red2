from __future__ import annotations

import logging
from typing import Dict

import httpx

from .oauth_service import OAuthService


logger = logging.getLogger(__name__)


NOTION_OAUTH_AUTH = "https://api.notion.com/v1/oauth/authorize"
NOTION_OAUTH_TOKEN = "https://api.notion.com/v1/oauth/token"
NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


class NotionService:
    """Minimal Notion API wrapper (OAuth or integration token).

    Provide either OAuth token (provider 'notion') or NOTION_TOKEN env via OAuthService provider config.
    """

    def __init__(self, oauth: OAuthService) -> None:
        self._oauth = oauth

    def _headers(self, uid: str = "owner") -> Dict[str, str]:
        tok = self._oauth.get_token(uid, "notion")
        if not tok:
            # Fallback: integration token via env (stored as provider client_secret for simplicity)
            cfg = self._oauth.provider("notion")
            if not (cfg and cfg.client_secret):
                raise RuntimeError("Notion not connected. Configure OAuth or NOTION_TOKEN")
            return {
                "Authorization": f"Bearer {cfg.client_secret}",
                "Notion-Version": NOTION_VERSION,
                "Content-Type": "application/json",
            }
        return {
            "Authorization": f"Bearer {tok.access_token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        }

    async def get_page(self, page_id: str, *, uid: str = "owner") -> Dict:
        url = f"{NOTION_API_BASE}/pages/{page_id}"
        async with httpx.AsyncClient(timeout=12.0) as client:
            r = await client.get(url, headers=self._headers(uid))
            if r.status_code != 200:
                raise RuntimeError(f"Notion get_page HTTP {r.status_code}: {r.text[:200]}")
            return r.json()

    async def search(self, query: str, *, uid: str = "owner") -> Dict:
        url = f"{NOTION_API_BASE}/search"
        async with httpx.AsyncClient(timeout=12.0) as client:
            r = await client.post(url, headers=self._headers(uid), json={"query": query})
            if r.status_code != 200:
                raise RuntimeError(f"Notion search HTTP {r.status_code}: {r.text[:200]}")
            return r.json()


from __future__ import annotations

import logging
from typing import Dict

import httpx

from .oauth_service import OAuthService
from .utils.retry_cache import with_backoff


logger = logging.getLogger(__name__)


YOUTUBE_SCOPE = "https://www.googleapis.com/auth/youtube.readonly"


class YouTubeDataService:
    """YouTube Data API v3 minimal wrapper (search/list)."""

    def __init__(self, oauth: OAuthService) -> None:
        self._oauth = oauth
        self._base = "https://www.googleapis.com/youtube/v3"

    def is_connected(self, uid: str = "owner") -> bool:
        return self._oauth.get_token(uid, "google") is not None

    def connect_link(self, uid: str = "owner") -> str:
        return self._oauth.build_authorize_url(
            "google",
            uid,
            extra_params={
                "scope": YOUTUBE_SCOPE + " openid email profile",
                "access_type": "offline",
                "include_granted_scopes": "true",
                "prompt": "consent",
            },
        )

    def _auth_header(self, uid: str = "owner") -> Dict[str, str]:
        tok = self._oauth.get_token(uid, "google")
        if not tok:
            raise RuntimeError("Google not connected. Use OAuth connect link")
        return {"Authorization": f"Bearer {tok.access_token}"}

    async def _request(self, method: str, url: str, *, uid: str = "owner", **kwargs) -> httpx.Response:
        headers = kwargs.pop("headers", {})
        headers.update(self._auth_header(uid))
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await with_backoff(lambda: client.request(method, url, headers=headers, **kwargs))
            return r

    async def search(self, q: str, *, uid: str = "owner", max_results: int = 10) -> Dict:
        url = f"{self._base}/search"
        params = {"q": q, "part": "snippet", "maxResults": max_results}
        r = await self._request("GET", url, uid=uid, params=params)
        if r.status_code != 200:
            raise RuntimeError(f"YouTube search HTTP {r.status_code}: {r.text[:200]}")
        return r.json()

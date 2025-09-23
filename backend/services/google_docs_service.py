from __future__ import annotations

import logging
from typing import Dict, Optional

import httpx

from .oauth_service import OAuthService
from .utils.retry_cache import with_backoff


logger = logging.getLogger(__name__)


GOOGLE_DOCS_SCOPE = "https://www.googleapis.com/auth/documents"


class GoogleDocsService:
    """Minimal Google Docs API v1 wrapper.

    Methods: create_doc, append_text, get_doc
    """

    def __init__(self, oauth: OAuthService) -> None:
        self._oauth = oauth
        self._base = "https://docs.googleapis.com/v1/documents"

    def is_connected(self, uid: str = "owner") -> bool:
        return self._oauth.get_token(uid, "google") is not None

    def connect_link(self, uid: str = "owner") -> str:
        scopes = " ".join([GOOGLE_DOCS_SCOPE, "openid", "email", "profile"])
        return self._oauth.build_authorize_url(
            "google",
            uid,
            extra_params={
                "scope": scopes,
                "access_type": "offline",
                "include_granted_scopes": "true",
                "prompt": "consent",
            },
        )

    def _auth_header(self, uid: str = "owner") -> Dict[str, str]:
        tok = self._oauth.get_token(uid, "google")
        if not tok:
            raise RuntimeError("Google not connected. Use /api/v1/oauth/... to connect")
        return {"Authorization": f"Bearer {tok.access_token}"}

    async def _request(self, method: str, url: str, *, uid: str = "owner", **kwargs) -> httpx.Response:
        headers = kwargs.pop("headers", {})
        headers.update(self._auth_header(uid))
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await with_backoff(lambda: client.request(method, url, headers=headers, **kwargs))
            if r.status_code == 401:
                tok = self._oauth.get_token(uid, "google")
                if tok and tok.refresh_token:
                    try:
                        new_tok = await self._oauth.refresh_token("google", tok.refresh_token)
                        self._oauth.save_token(uid, "google", new_tok)
                        headers = kwargs.pop("headers", {})
                        headers.update({"Authorization": f"Bearer {new_tok.access_token}"})
                        return await with_backoff(lambda: client.request(method, url, headers=headers, **kwargs))
                    except Exception:
                        pass
            return r

    async def create_doc(self, title: str, *, uid: str = "owner") -> Dict:
        url = self._base
        payload = {"title": title}
        r = await self._request("POST", url, uid=uid, json=payload)
        if r.status_code not in (200, 201):
            raise RuntimeError(f"Docs create HTTP {r.status_code}: {r.text[:200]}")
        return r.json()

    async def append_text(self, document_id: str, text: str, *, uid: str = "owner") -> Dict:
        url = f"{self._base}/{document_id}:batchUpdate"
        requests = [
            {"insertText": {"location": {"index": 1_000_000_000}, "text": text}},
        ]
        r = await self._request("POST", url, uid=uid, json={"requests": requests})
        if r.status_code not in (200, 201):
            raise RuntimeError(f"Docs update HTTP {r.status_code}: {r.text[:200]}")
        return r.json()

    async def get_doc(self, document_id: str, *, uid: str = "owner") -> Dict:
        url = f"{self._base}/{document_id}"
        r = await self._request("GET", url, uid=uid)
        if r.status_code != 200:
            raise RuntimeError(f"Docs get HTTP {r.status_code}: {r.text[:200]}")
        return r.json()

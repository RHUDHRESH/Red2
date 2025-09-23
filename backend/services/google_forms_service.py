from __future__ import annotations

import logging
from typing import Dict

import httpx

from .oauth_service import OAuthService
from .utils.retry_cache import with_backoff


logger = logging.getLogger(__name__)


GOOGLE_FORMS_SCOPE = "https://www.googleapis.com/auth/forms.body https://www.googleapis.com/auth/forms.responses.readonly"


class GoogleFormsService:
    """Google Forms API v1 wrapper (create forms and read responses)."""

    def __init__(self, oauth: OAuthService) -> None:
        self._oauth = oauth
        self._base = "https://forms.googleapis.com/v1/forms"

    def is_connected(self, uid: str = "owner") -> bool:
        return self._oauth.get_token(uid, "google") is not None

    def connect_link(self, uid: str = "owner") -> str:
        return self._oauth.build_authorize_url(
            "google",
            uid,
            extra_params={
                "scope": GOOGLE_FORMS_SCOPE + " openid email profile",
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

    async def create_form(self, title: str, description: str = "", *, uid: str = "owner") -> Dict:
        payload = {"info": {"title": title, "documentTitle": title, "description": description}}
        r = await self._request("POST", self._base, uid=uid, json=payload)
        if r.status_code not in (200, 201):
            raise RuntimeError(f"Forms create HTTP {r.status_code}: {r.text[:200]}")
        return r.json()

    async def get_responses(self, form_id: str, *, uid: str = "owner") -> Dict:
        url = f"{self._base}/{form_id}/responses"
        r = await self._request("GET", url, uid=uid)
        if r.status_code != 200:
            raise RuntimeError(f"Forms responses HTTP {r.status_code}: {r.text[:200]}")
        return r.json()

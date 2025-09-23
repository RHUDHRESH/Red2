from __future__ import annotations

import logging
from typing import Dict

import httpx

from .oauth_service import OAuthService
from .utils.retry_cache import with_backoff


logger = logging.getLogger(__name__)


GOOGLE_CAL_SCOPE = "https://www.googleapis.com/auth/calendar"


class GoogleCalendarService:
    """Google Calendar API v3 wrapper (list/create/update/delete)."""

    def __init__(self, oauth: OAuthService) -> None:
        self._oauth = oauth
        self._base = "https://www.googleapis.com/calendar/v3"

    def is_connected(self, uid: str = "owner") -> bool:
        return self._oauth.get_token(uid, "google") is not None

    def connect_link(self, uid: str = "owner") -> str:
        return self._oauth.build_authorize_url(
            "google",
            uid,
            extra_params={
                "scope": GOOGLE_CAL_SCOPE + " openid email profile",
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

    async def list_events(self, calendar_id: str = "primary", *, uid: str = "owner", **params) -> Dict:
        url = f"{self._base}/calendars/{calendar_id}/events"
        r = await self._request("GET", url, uid=uid, params=params)
        if r.status_code != 200:
            raise RuntimeError(f"Calendar list HTTP {r.status_code}: {r.text[:200]}")
        return r.json()

    async def create_event(self, event: Dict, calendar_id: str = "primary", *, uid: str = "owner") -> Dict:
        url = f"{self._base}/calendars/{calendar_id}/events"
        r = await self._request("POST", url, uid=uid, json=event)
        if r.status_code not in (200, 201):
            raise RuntimeError(f"Calendar create HTTP {r.status_code}: {r.text[:200]}")
        return r.json()

    async def update_event(self, event_id: str, event: Dict, calendar_id: str = "primary", *, uid: str = "owner") -> Dict:
        url = f"{self._base}/calendars/{calendar_id}/events/{event_id}"
        r = await self._request("PUT", url, uid=uid, json=event)
        if r.status_code not in (200, 201):
            raise RuntimeError(f"Calendar update HTTP {r.status_code}: {r.text[:200]}")
        return r.json()

    async def delete_event(self, event_id: str, calendar_id: str = "primary", *, uid: str = "owner") -> bool:
        url = f"{self._base}/calendars/{calendar_id}/events/{event_id}"
        r = await self._request("DELETE", url, uid=uid)
        if r.status_code not in (200, 204):
            raise RuntimeError(f"Calendar delete HTTP {r.status_code}: {r.text[:200]}")
        return True

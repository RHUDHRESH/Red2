from __future__ import annotations

import base64
import logging
from email.message import EmailMessage
from typing import Dict

import httpx

from .oauth_service import OAuthService
from .utils.retry_cache import with_backoff


logger = logging.getLogger(__name__)


GMAIL_SCOPE = "https://www.googleapis.com/auth/gmail.send"


class GmailService:
    """Gmail API v1 minimal client (send-only)."""

    def __init__(self, oauth: OAuthService) -> None:
        self._oauth = oauth
        self._base = "https://gmail.googleapis.com/gmail/v1/users"

    def is_connected(self, uid: str = "owner") -> bool:
        return self._oauth.get_token(uid, "google") is not None

    def connect_link(self, uid: str = "owner") -> str:
        return self._oauth.build_authorize_url(
            "google",
            uid,
            extra_params={
                "scope": GMAIL_SCOPE + " openid email profile",
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

    async def send(self, sender_email: str, to: str, subject: str, body: str, *, uid: str = "owner") -> Dict:
        msg = EmailMessage()
        msg["To"] = to
        msg["From"] = sender_email
        msg["Subject"] = subject
        msg.set_content(body)
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")
        url = f"{self._base}/me/messages/send"
        r = await self._request("POST", url, uid=uid, json={"raw": raw})
        if r.status_code not in (200, 201):
            raise RuntimeError(f"Gmail send HTTP {r.status_code}: {r.text[:200]}")
        return r.json()

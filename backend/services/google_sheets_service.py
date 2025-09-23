from __future__ import annotations

import logging
from typing import List, Optional, Dict, Any

import httpx

from .oauth_service import OAuthService
from .utils.retry_cache import with_backoff


logger = logging.getLogger(__name__)


GOOGLE_SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets"


class GoogleSheetsService:
    """
    Minimal Google Sheets API v4 client using OAuthService tokens.

    Default user is the single-owner account (uid="owner").
    """

    def __init__(self, oauth: OAuthService) -> None:
        self._oauth = oauth
        self._base = "https://sheets.googleapis.com/v4/spreadsheets"

    def is_connected(self, uid: str = "owner") -> bool:
        return self._oauth.get_token(uid, "google") is not None

    def connect_link(self, uid: str = "owner") -> str:
        # Ask for offline access to obtain refresh_token; prompt consent to ensure refresh_token issuance
        scopes = " ".join([GOOGLE_SHEETS_SCOPE, "openid", "email", "profile"])  # include OIDC for cohesion
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
            raise RuntimeError("Google not connected. Use /api/v1/google-sheets/connect-link")
        return {"Authorization": f"Bearer {tok.access_token}"}

    async def _request(self, method: str, url: str, *, uid: str = "owner", **kwargs) -> httpx.Response:
        headers = kwargs.pop("headers", {})
        headers.update(self._auth_header(uid))
        # First attempt with backoff
        async with httpx.AsyncClient(timeout=12.0) as client:
            r = await with_backoff(lambda: client.request(method, url, headers=headers, **kwargs))
            if r.status_code != 401:
                return r
        # If unauthorized and we have a refresh token, try to refresh once
        tok = self._oauth.get_token(uid, "google")
        if tok and tok.refresh_token:
            try:
                new_tok = await self._oauth.refresh_token("google", tok.refresh_token)
                self._oauth.save_token(uid, "google", new_tok)
                headers = kwargs.pop("headers", {})
                headers.update({"Authorization": f"Bearer {new_tok.access_token}"})
                async with httpx.AsyncClient(timeout=12.0) as client:
                    return await with_backoff(lambda: client.request(method, url, headers=headers, **kwargs))
            except Exception as e:
                logger.warning(f"[sheets] token refresh failed: {e}")
        return r

    async def get_values(self, spreadsheet_id: str, range_a1: str, *, uid: str = "owner") -> List[List[Any]]:
        url = f"{self._base}/{spreadsheet_id}/values/{range_a1}"
        r = await self._request("GET", url, uid=uid)
        if r.status_code != 200:
            raise RuntimeError(f"Sheets get_values HTTP {r.status_code}: {r.text[:200]}")
        data = r.json()
        return data.get("values", [])

    async def append_values(
        self,
        spreadsheet_id: str,
        range_a1: str,
        values: List[List[Any]],
        *,
        uid: str = "owner",
        value_input_option: str = "USER_ENTERED",
    ) -> Dict:
        url = f"{self._base}/{spreadsheet_id}/values/{range_a1}:append"
        params = {"valueInputOption": value_input_option}
        body = {"range": range_a1, "majorDimension": "ROWS", "values": values}
        r = await self._request("POST", url, uid=uid, params=params, json=body)
        if r.status_code not in (200, 201):
            raise RuntimeError(f"Sheets append_values HTTP {r.status_code}: {r.text[:200]}")
        return r.json()

    async def update_values(
        self,
        spreadsheet_id: str,
        range_a1: str,
        values: List[List[Any]],
        *,
        uid: str = "owner",
        value_input_option: str = "USER_ENTERED",
    ) -> Dict:
        url = f"{self._base}/{spreadsheet_id}/values/{range_a1}"
        params = {"valueInputOption": value_input_option}
        body = {"range": range_a1, "majorDimension": "ROWS", "values": values}
        r = await self._request("PUT", url, uid=uid, params=params, json=body)
        if r.status_code not in (200, 201):
            raise RuntimeError(f"Sheets update_values HTTP {r.status_code}: {r.text[:200]}")
        return r.json()

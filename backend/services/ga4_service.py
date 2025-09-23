from __future__ import annotations

import logging
from typing import Dict, List

import httpx

from .oauth_service import OAuthService
from .utils.retry_cache import with_backoff


logger = logging.getLogger(__name__)


GA4_SCOPE = "https://www.googleapis.com/auth/analytics.readonly"


class GA4Service:
    """Google Analytics Data API (GA4) minimal wrapper for runReport."""

    def __init__(self, oauth: OAuthService) -> None:
        self._oauth = oauth
        self._base = "https://analyticsdata.googleapis.com/v1beta"

    def is_connected(self, uid: str = "owner") -> bool:
        return self._oauth.get_token(uid, "google") is not None

    def connect_link(self, uid: str = "owner") -> str:
        return self._oauth.build_authorize_url(
            "google",
            uid,
            extra_params={
                "scope": GA4_SCOPE + " openid email profile",
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

    async def run_report(
        self,
        property_id: str,
        *,
        dimensions: List[Dict],
        metrics: List[Dict],
        date_ranges: List[Dict],
        uid: str = "owner",
    ) -> Dict:
        url = f"{self._base}/properties/{property_id}:runReport"
        headers = self._auth_header(uid)
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await with_backoff(lambda: client.post(
                url,
                headers={**headers, "Content-Type": "application/json"},
                json={
                    "dimensions": dimensions,
                    "metrics": metrics,
                    "dateRanges": date_ranges,
                },
            ))
            if r.status_code != 200:
                raise RuntimeError(f"GA4 runReport HTTP {r.status_code}: {r.text[:200]}")
            return r.json()

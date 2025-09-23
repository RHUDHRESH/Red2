from __future__ import annotations

import json
import os
import secrets
import time
from dataclasses import dataclass
from typing import Dict, Optional

import httpx

from core.config import settings, BACKEND_DIR
from schemas.oauth_schemas import OAuthToken


@dataclass
class ProviderConfig:
    name: str
    auth_url: str
    token_url: str
    client_id: Optional[str]
    client_secret: Optional[str]
    scopes: list[str]
    redirect_path: str


class OAuthService:
    """
    Minimal generic OAuth 2.0 service (authorization code flow).
    - Stores tokens in-memory and persists to backend/.oauth_tokens.json best-effort.
    - Builds provider authorize URLs and exchanges codes for tokens.
    - Designed for frontend to open authorize_link in a popup and call callback endpoint.
    Security note: For production, back tokens with encrypted storage tied to an authenticated user.
    """

    def __init__(self) -> None:
        self._state_store: Dict[str, Dict] = {}
        self._tokens: Dict[str, Dict[str, OAuthToken]] = {}
        self._path = BACKEND_DIR / ".oauth_tokens.json"
        self._providers: Dict[str, ProviderConfig] = self._load_providers()
        self._load()

    def _load_providers(self) -> Dict[str, ProviderConfig]:
        base = settings.PUBLIC_BASE_URL.rstrip("/")
        providers: Dict[str, ProviderConfig] = {}

        # Canva provider from env-configured endpoints (if provided)
        canva_auth = os.getenv("OAUTH_CANVA_AUTH_URL", "").strip()
        canva_token = os.getenv("OAUTH_CANVA_TOKEN_URL", "").strip()
        providers["canva"] = ProviderConfig(
            name="canva",
            auth_url=canva_auth,
            token_url=canva_token,
            client_id=os.getenv("CANVA_CLIENT_ID"),
            client_secret=os.getenv("CANVA_CLIENT_SECRET"),
            scopes=[s for s in os.getenv("CANVA_SCOPES", "").split(" ") if s],
            redirect_path="/api/v1/oauth/callback/canva",
        )

        # LinkedIn built-in example
        providers["linkedin"] = ProviderConfig(
            name="linkedin",
            auth_url="https://www.linkedin.com/oauth/v2/authorization",
            token_url="https://www.linkedin.com/oauth/v2/accessToken",
            client_id=os.getenv("LINKEDIN_CLIENT_ID"),
            client_secret=os.getenv("LINKEDIN_CLIENT_SECRET"),
            scopes=["r_liteprofile", "r_emailaddress", "w_member_social"],
            redirect_path="/api/v1/oauth/callback/linkedin",
        )

        # Google example (OpenID; adjust scopes per use)
        providers["google"] = ProviderConfig(
            name="google",
            auth_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            client_id=os.getenv("GOOGLE_CLIENT_ID"),
            client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
            scopes=["openid", "email", "profile"],
            redirect_path="/api/v1/auth/callback/google",
        )

        # Notion OAuth (optional)
        providers["notion"] = ProviderConfig(
            name="notion",
            auth_url=os.getenv("NOTION_OAUTH_AUTH_URL", "https://api.notion.com/v1/oauth/authorize"),
            token_url=os.getenv("NOTION_OAUTH_TOKEN_URL", "https://api.notion.com/v1/oauth/token"),
            client_id=os.getenv("NOTION_CLIENT_ID"),
            client_secret=os.getenv("NOTION_CLIENT_SECRET"),
            scopes=[],
            redirect_path="/api/v1/oauth/callback/notion",
        )

        # Discord OAuth (optional; for user identity/authorization)
        providers["discord"] = ProviderConfig(
            name="discord",
            auth_url="https://discord.com/api/oauth2/authorize",
            token_url="https://discord.com/api/oauth2/token",
            client_id=os.getenv("DISCORD_CLIENT_ID"),
            client_secret=os.getenv("DISCORD_CLIENT_SECRET"),
            scopes=["identify"],
            redirect_path="/api/v1/oauth/callback/discord",
        )

        return providers

    def _persist(self) -> None:
        try:
            data = {
                uid: {p: t.raw or t.__dict__ for p, t in mp.items()}
                for uid, mp in self._tokens.items()
            }
            self._path.write_text(json.dumps(data))
        except Exception:
            pass

    def _load(self) -> None:
        try:
            if self._path.exists():
                raw = json.loads(self._path.read_text())
                for uid, mp in raw.items():
                    self._tokens[uid] = {}
                    for p, td in mp.items():
                        if isinstance(td, dict) and "access_token" in td:
                            self._tokens[uid][p] = OAuthToken(**{**td, "raw": td})
        except Exception:
            pass

    def provider(self, name: str) -> Optional[ProviderConfig]:
        return self._providers.get(name)

    def providers_info(self) -> Dict[str, Dict]:
        out: Dict[str, Dict] = {}
        for k, v in self._providers.items():
            enabled = bool(v.client_id and v.client_secret and v.auth_url and v.token_url)
            out[k] = {
                "name": v.name,
                "enabled": enabled,
                "auth_url": v.auth_url or None,
                "token_url": v.token_url or None,
                "scopes": v.scopes,
            }
        return out

    def build_authorize_url(self, provider: str, uid: str, extra_params: Optional[Dict] = None) -> str:
        cfg = self.provider(provider)
        if not cfg or not (cfg.client_id and cfg.auth_url):
            raise ValueError(f"Provider '{provider}' not configured")

        base = settings.PUBLIC_BASE_URL.rstrip("/")
        redirect_uri = f"{base}{cfg.redirect_path}"
        state = secrets.token_urlsafe(24)
        self._state_store[state] = {"provider": provider, "uid": uid, "ts": int(time.time())}

        import urllib.parse as up
        params = {
            "response_type": "code",
            "client_id": cfg.client_id,
            "redirect_uri": redirect_uri,
            "scope": " ".join(cfg.scopes),
            "state": state,
        }
        if extra_params:
            params.update(extra_params)
        return cfg.auth_url + ("&" if "?" in cfg.auth_url else "?") + up.urlencode(params)

    async def exchange_code(self, provider: str, code: str) -> OAuthToken:
        cfg = self.provider(provider)
        if not cfg or not (cfg.client_id and cfg.client_secret and cfg.token_url):
            raise ValueError(f"Provider '{provider}' not configured")
        base = settings.PUBLIC_BASE_URL.rstrip("/")
        redirect_uri = f"{base}{cfg.redirect_path}"
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": cfg.client_id,
            "client_secret": cfg.client_secret,
        }
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(cfg.token_url, data=data, headers={"Accept": "application/json"})
            r.raise_for_status()
            payload = r.json()
            tok = OAuthToken(
                access_token=payload.get("access_token", ""),
                token_type=payload.get("token_type") or "Bearer",
                expires_in=payload.get("expires_in"),
                refresh_token=payload.get("refresh_token"),
                scope=payload.get("scope"),
                raw=payload,
            )
            return tok

    async def refresh_token(self, provider: str, refresh_token: str) -> OAuthToken:
        cfg = self.provider(provider)
        if not cfg or not (cfg.client_id and cfg.client_secret and cfg.token_url):
            raise ValueError(f"Provider '{provider}' not configured")
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": cfg.client_id,
            "client_secret": cfg.client_secret,
        }
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(cfg.token_url, data=data, headers={"Accept": "application/json"})
            r.raise_for_status()
            payload = r.json()
            tok = OAuthToken(
                access_token=payload.get("access_token", ""),
                token_type=payload.get("token_type") or "Bearer",
                expires_in=payload.get("expires_in"),
                refresh_token=payload.get("refresh_token") or refresh_token,
                scope=payload.get("scope"),
                raw=payload,
            )
            return tok

    def save_token(self, uid: str, provider: str, token: OAuthToken) -> None:
        self._tokens.setdefault(uid, {})[provider] = token
        self._persist()

    def get_token(self, uid: str, provider: str) -> Optional[OAuthToken]:
        return self._tokens.get(uid, {}).get(provider)

    def revoke(self, uid: str, provider: str) -> None:
        if uid in self._tokens and provider in self._tokens[uid]:
            del self._tokens[uid][provider]
            if not self._tokens[uid]:
                del self._tokens[uid]
            self._persist()

    def consume_state(self, state: str) -> Optional[Dict]:
        return self._state_store.pop(state, None)

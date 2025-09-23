from __future__ import annotations

from typing import Dict, Optional
from pydantic import BaseModel, Field


class OAuthProviderInfo(BaseModel):
    name: str
    enabled: bool = False
    auth_url: Optional[str] = None
    token_url: Optional[str] = None
    scopes: list[str] = Field(default_factory=list)
    authorize_link: Optional[str] = None


class OAuthToken(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: Optional[int] = None
    refresh_token: Optional[str] = None
    scope: Optional[str] = None
    raw: Dict = Field(default_factory=dict)


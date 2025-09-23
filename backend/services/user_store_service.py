from __future__ import annotations

import json
import secrets
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Optional

from core.config import BACKEND_DIR


@dataclass
class User:
    id: str
    email: str
    name: str
    picture: Optional[str] = None
    provider: str = "google"
    provider_sub: Optional[str] = None
    is_owner: bool = False
    created_at: int = 0
    updated_at: int = 0


class UserStoreService:
    """Tiny local user + session store for single-user setups.

    Data files:
    - backend/.users.json
    - backend/.sessions.json
    """

    def __init__(self) -> None:
        self._users_path = BACKEND_DIR / ".users.json"
        self._sessions_path = BACKEND_DIR / ".sessions.json"
        self._users: Dict[str, User] = {}
        self._by_provider: Dict[str, Dict[str, str]] = {}  # provider -> sub -> user_id
        self._sessions: Dict[str, Dict[str, str]] = {}  # token -> {user_id, created_at}
        self._load()

    def _load(self) -> None:
        try:
            if self._users_path.exists():
                raw = json.loads(self._users_path.read_text())
                for uid, u in raw.get("users", {}).items():
                    user = User(**u)
                    self._users[uid] = user
                    if user.provider and user.provider_sub:
                        self._by_provider.setdefault(user.provider, {})[user.provider_sub] = uid
        except Exception:
            pass
        try:
            if self._sessions_path.exists():
                self._sessions = json.loads(self._sessions_path.read_text()) or {}
        except Exception:
            pass

    def _persist(self) -> None:
        try:
            payload = {
                "users": {uid: asdict(u) for uid, u in self._users.items()},
            }
            self._users_path.write_text(json.dumps(payload))
        except Exception:
            pass
        try:
            self._sessions_path.write_text(json.dumps(self._sessions))
        except Exception:
            pass

    def upsert_user_google(self, sub: str, email: str, name: str, picture: Optional[str]) -> User:
        # Existing?
        uid = self._by_provider.get("google", {}).get(sub)
        now = int(time.time())
        if uid and uid in self._users:
            u = self._users[uid]
            u.email = email or u.email
            u.name = name or u.name
            u.picture = picture or u.picture
            u.updated_at = now
            self._persist()
            return u
        # Create new
        uid = secrets.token_hex(16)
        is_owner = not any(u.is_owner for u in self._users.values())
        u = User(
            id=uid,
            email=email,
            name=name,
            picture=picture,
            provider="google",
            provider_sub=sub,
            is_owner=is_owner,
            created_at=now,
            updated_at=now,
        )
        self._users[uid] = u
        self._by_provider.setdefault("google", {})[sub] = uid
        self._persist()
        return u

    def create_session(self, user_id: str) -> str:
        token = secrets.token_urlsafe(32)
        self._sessions[token] = {"user_id": user_id, "created_at": str(int(time.time()))}
        self._persist()
        return token

    def get_user_by_session(self, token: str) -> Optional[User]:
        data = self._sessions.get(token)
        if not data:
            return None
        uid = data.get("user_id")
        if not uid:
            return None
        return self._users.get(uid)

    def revoke_session(self, token: str) -> None:
        if token in self._sessions:
            del self._sessions[token]
            self._persist()


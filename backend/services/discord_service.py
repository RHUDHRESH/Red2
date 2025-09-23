from __future__ import annotations

import logging
from typing import Dict, Optional

import httpx


logger = logging.getLogger(__name__)


class DiscordService:
    """Discord REST minimal client.

    Supports bot token (env DISCORD_BOT_TOKEN wired via OAuthService provider config) for POSTing messages.
    """

    def __init__(self, bot_token: Optional[str] = None) -> None:
        self._bot_token = bot_token
        self._base = "https://discord.com/api/v10"

    def is_connected(self) -> bool:
        return bool(self._bot_token)

    def set_bot_token(self, token: str) -> None:
        self._bot_token = token

    async def send_message(self, channel_id: str, content: str) -> Dict:
        if not self._bot_token:
            raise RuntimeError("Discord bot token not configured")
        url = f"{self._base}/channels/{channel_id}/messages"
        headers = {"Authorization": f"Bot {self._bot_token}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=12.0) as client:
            r = await client.post(url, headers=headers, json={"content": content})
            if r.status_code not in (200, 201):
                raise RuntimeError(f"Discord send HTTP {r.status_code}: {r.text[:200]}")
            return r.json()


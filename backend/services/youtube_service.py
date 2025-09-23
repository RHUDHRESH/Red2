from __future__ import annotations

import logging
from typing import List, Optional
from urllib.parse import urlparse, parse_qs

try:
    from youtube_transcript_api import YouTubeTranscriptApi
except Exception:  # pragma: no cover
    YouTubeTranscriptApi = None  # type: ignore


logger = logging.getLogger(__name__)


def _extract_video_id(url: str) -> Optional[str]:
    try:
        u = urlparse(url)
        if u.netloc.endswith("youtu.be"):
            vid = u.path.strip("/")
            return vid if vid else None
        if "youtube.com" in u.netloc:
            qs = parse_qs(u.query)
            if "v" in qs:
                return qs["v"][0]
            # Short /embed/VIDEOID
            if u.path.startswith("/embed/"):
                return u.path.split("/")[-1]
    except Exception:
        pass
    return None


class YouTubeService:
    """Fetch YouTube transcripts when available (no API key).

    Uses youtube-transcript-api package. Falls back gracefully if missing.
    """

    async def get_transcript(self, url_or_id: str, *, languages: Optional[List[str]] = None) -> str:
        if YouTubeTranscriptApi is None:
            logger.warning("youtube-transcript-api not installed; transcript disabled")
            return ""
        vid = url_or_id
        if "://" in url_or_id:
            vid = _extract_video_id(url_or_id) or ""
        if not vid:
            return ""
        try:
            langs = languages or ["en", "en-IN"]
            parts = YouTubeTranscriptApi.get_transcript(vid, languages=langs)
            return " ".join(p.get("text", "") for p in parts)
        except Exception as e:
            logger.warning(f"[youtube] transcript fetch failed for {url_or_id}: {e}")
            return ""


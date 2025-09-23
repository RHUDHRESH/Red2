from __future__ import annotations

import io
import logging
from typing import Optional

import httpx
from pdfminer.high_level import extract_text


logger = logging.getLogger(__name__)


class PDFService:
    """Fetch and extract text from PDFs via pdfminer.six.

    - fetch(url) → bytes
    - extract(bytes) → text
    - fetch_and_extract(url) → text
    """

    async def fetch(self, url: str, *, timeout: float = 15.0) -> Optional[bytes]:
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                r = await client.get(url)
                r.raise_for_status()
                ctype = r.headers.get("content-type", "").lower()
                if "pdf" not in ctype and not url.lower().endswith(".pdf"):
                    logger.warning(f"[pdf] content-type not pdf for {url}: {ctype}")
                return r.content
        except Exception as e:
            logger.warning(f"[pdf] fetch failed for {url}: {e}")
            return None

    def extract(self, data: bytes) -> str:
        try:
            with io.BytesIO(data) as bio:
                text = extract_text(bio)
                return text or ""
        except Exception as e:
            logger.warning(f"[pdf] extract failed: {e}")
            return ""

    async def fetch_and_extract(self, url: str) -> str:
        data = await self.fetch(url)
        return self.extract(data) if data else ""


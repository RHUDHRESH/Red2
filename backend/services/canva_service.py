from __future__ import annotations

import base64
import csv
import io
import os
from typing import Dict, List, Optional

from langchain_ollama.chat_models import ChatOllama


class CanvaService:
    """
    Lightweight Canva connector facade.

    Notes on capabilities and constraints:
    - Canva's public developer platform focuses on Apps that run inside Canva
      (Import/Publish integrations) and does not expose a general-purpose REST API
      to programmatically create and finalize designs server-side.
    - For now, we support two useful paths:
        1) Generate a precise design brief (layout, copy, palette) from description
           that a user can apply with a pre-shared Canva template link.
        2) Emit a Bulk Create CSV (base64) for templates that use variables.
    - If you provide a template duplication link via CANVA_TEMPLATE_URL, we will
      return it so the user can click and start with your template directly.

    This class is designed to be extended if a server-side Canva design API becomes
    available or if you add a custom Canva App front-end that consumes the brief.
    """

    def __init__(self, llm: Optional[ChatOllama] = None) -> None:
        self._llm = llm
        self._template_url = os.getenv("CANVA_TEMPLATE_URL", "").strip()
        self._brand_colors = [c.strip() for c in os.getenv("CANVA_BRAND_COLORS", "").split(",") if c.strip()]

    @property
    def template_url(self) -> str:
        return self._template_url

    def build_design_brief(self, description: str, format_hint: str = "instagram_post") -> Dict:
        """
        Produce a structured design brief from a natural-language description.
        The brief includes: format, palette, typography hints, text blocks, and layout notes.
        """
        # If an LLM is available, use it to enrich the brief; else simple heuristic
        if self._llm is None:
            palette = self._brand_colors or ["#6420FF", "#111111", "#FFFFFF"]
            return {
                "format": format_hint,
                "palette": palette,
                "typography": {"heading": "Canva Sans", "body": "Canva Sans"},
                "blocks": [
                    {"type": "heading", "text": description[:80]},
                    {"type": "subheading", "text": "Compelling subhead with benefit"},
                    {"type": "body", "text": "Short body copy and a clear CTA"},
                ],
                "layout": {"style": "clean", "image_ratio": "1:1", "cta_style": "button"},
            }

        from langchain_core.prompts import ChatPromptTemplate

        prompt = ChatPromptTemplate.from_messages([
            ("system", "You generate compact JSON design briefs for Canva templates. "
                       "Fields: format, palette (hex), typography{heading,body}, blocks[list of {type,text}], layout{style,image_ratio,cta_style}. "
                       "Keep text concise and practical."),
            ("human", "Description: {d}\nFormat: {f}\nBrand colors: {colors}"),
        ])
        res = (prompt | self._llm).invoke({
            "d": description,
            "f": format_hint,
            "colors": ", ".join(self._brand_colors) if self._brand_colors else "",
        }).content

        # Best-effort parse; if not JSON, wrap as a single block
        try:
            import json
            data = json.loads(res)
            if isinstance(data, dict):
                return data
        except Exception:
            pass

        palette = self._brand_colors or ["#6420FF", "#111111", "#FFFFFF"]
        return {
            "format": format_hint,
            "palette": palette,
            "typography": {"heading": "Canva Sans", "body": "Canva Sans"},
            "blocks": [{"type": "heading", "text": description[:80]}],
            "layout": {"style": "clean", "image_ratio": "1:1", "cta_style": "button"},
        }

    def build_bulk_create_csv_base64(self, rows: List[Dict[str, str]]) -> str:
        """
        Create a CSV (base64) suitable for Canva Bulk Create templates where
        variable names correspond to CSV headers.
        """
        if not rows:
            return ""
        headers = list(rows[0].keys())
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=headers)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k, "") for k in headers})
        return base64.b64encode(buf.getvalue().encode("utf-8")).decode("ascii")

    def get_handoff_link(self) -> Optional[str]:
        """
        Return a template duplication link, if configured via CANVA_TEMPLATE_URL.
        Users can click this to open Canva with your template and apply the brief.
        """
        return self._template_url or None


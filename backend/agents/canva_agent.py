from __future__ import annotations

import base64
from typing import Dict

from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama.chat_models import ChatOllama

from services.registry import get_services
from services.canva_service import CanvaService
from schemas.canva_schemas import CanvaDesignRequest, CanvaDesignResponse


def _llm() -> ChatOllama:
    try:
        return get_services().llm_reasoning
    except Exception:
        return ChatOllama(model="gemma3:4b", temperature=0.2)


async def run_canva_design(req: CanvaDesignRequest) -> CanvaDesignResponse:
    services = get_services()
    canva: CanvaService = services.canva

    # 1) Create a design brief (palette, blocks, layout) from description
    brief = canva.build_design_brief(req.description, req.format_hint)

    # 2) Optionally produce a Bulk Create CSV when variants > 1
    bulk_csv_b64 = None
    if req.variants > 1:
        rows = []
        # Use LLM to generate concise variant text lines (e.g., headlines)
        prompt = ChatPromptTemplate.from_messages([
            ("system", "Generate {n} concise marketing headlines based on the description. Return one per line."),
            ("human", "Description: {d}")
        ])
        text = (prompt | _llm()).invoke({"n": req.variants, "d": req.description}).content
        variants = [ln.strip("- • ") for ln in text.splitlines() if ln.strip()][: req.variants]
        for v in variants:
            rows.append({"headline": v, "cta": "Learn more"})
        bulk_csv_b64 = canva.build_bulk_create_csv_base64(rows)

    # 3) Handoff link (template duplication link) if configured
    template_link = canva.get_handoff_link()

    notes = (
        "Click the Canva template link to duplicate the design, then apply the brief. "
        "If using Bulk Create, upload the CSV to your template's variables."
    )

    return CanvaDesignResponse(
        template_link=template_link,
        design_brief=brief,
        bulk_create_csv_base64=bulk_csv_b64,
        notes=notes,
    )


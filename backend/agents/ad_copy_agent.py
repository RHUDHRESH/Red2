import logging
from typing import TypedDict, List

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_ollama.chat_models import ChatOllama
from langgraph.graph import StateGraph, END

from services.registry import get_services
from schemas.asset_schemas import AdCopyRequest, AdCopyResponse, AdVariant
from .utils.postprocess import clamp_length


logger = logging.getLogger(__name__)


class AdState(TypedDict):
    req: AdCopyRequest
    resp: AdCopyResponse | None
    error: str | None


class VariantsTool(BaseModel):
    variants: List[AdVariant] = Field(default_factory=list)


def _llm() -> ChatOllama:
    try:
        return get_services().llm_reasoning
    except Exception:
        return ChatOllama(model="gemma3:4b", temperature=0.3)


async def draft_ads(state: AdState) -> AdState:
    logger.info("[adcopy] ▶ drafting ad variants …")
    tool = _llm().with_structured_output(VariantsTool)
    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a performance marketer. Generate platform-appropriate ad copy variants."
         " For Facebook/Instagram/LinkedIn: provide primary text (1-3 lines), a short headline (<=40 chars), and description (<=90 chars)."
         " For Google Search: craft RSA-like headlines (<=30 chars) in 'headline' and a description (<=90 chars)."),
        ("human",
         "Product summary: {summary}\nOffer: {offer}\nCTA: {cta}\nTone: {tone}\nLanguage: {lang}\nPlatforms: {platforms}")
    ])
    req = state["req"]
    chain = prompt | tool
    res = await chain.ainvoke({
        "summary": req.product_summary,
        "offer": req.offer,
        "cta": req.call_to_action,
        "tone": req.tone,
        "lang": req.language,
        "platforms": ", ".join(req.platforms),
    })
    # Filter to requested platforms and enforce length constraints
    variants = [v for v in res.variants if v.platform.lower() in {p.lower() for p in req.platforms}]
    cleaned: list[AdVariant] = []
    for v in variants:
        plat = (v.platform or "").lower()
        primary = v.primary_text or ""
        head = v.headline or ""
        desc = v.description or ""
        if plat in ("facebook", "instagram", "linkedin"):
            head = clamp_length(head, 40)
            desc = clamp_length(desc, 90)
        elif plat == "google_search":
            head = clamp_length(head, 30)
            desc = clamp_length(desc, 90)
        cleaned.append(AdVariant(platform=v.platform, primary_text=primary, headline=head, description=desc))
    state["resp"] = AdCopyResponse(variants=cleaned[: max(3, len(req.platforms) * 2)])
    return state


def build_adcopy_graph():
    wf = StateGraph(AdState)
    wf.add_node("draft", draft_ads)
    wf.set_entry_point("draft")
    wf.add_edge("draft", END)
    return wf.compile()


adcopy_graph = build_adcopy_graph()


async def run_ad_copy(req_dict: dict) -> dict:
    logger.info("--- Running Ad Copy Agent ---")
    try:
        req = AdCopyRequest(**req_dict)
        init: AdState = {"req": req, "resp": None, "error": None}
        final = await adcopy_graph.ainvoke(init)
        if final.get("error"):
            return {"error": final["error"]}
        return final["resp"].model_dump()
    except Exception as e:
        logger.error(f"[adcopy] critical error: {e}", exc_info=True)
        return {"error": "A critical error occurred while generating ad copy."}

import logging
from typing import TypedDict

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_ollama.chat_models import ChatOllama
from langgraph.graph import StateGraph, END

from services.registry import get_services
from schemas.asset_schemas import CtaRequest, CtaResponse
from .utils.postprocess import top_unique


logger = logging.getLogger(__name__)


class CTAState(TypedDict):
    req: CtaRequest
    resp: CtaResponse | None
    error: str | None


class CTATool(BaseModel):
    ctas: list[str] = Field(default_factory=list)


def _llm() -> ChatOllama:
    try:
        return get_services().llm_fast
    except Exception:
        return ChatOllama(model="gemma3:1b", temperature=0.0)


async def draft_ctas(state: CTAState) -> CTAState:
    logger.info("[cta] ▶ drafting CTA lines …")
    tool = _llm().with_structured_output(CTATool)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Generate short, varied CTAs (1-5 words), imperative mood, no punctuation overload. Avoid emojis."),
        ("human", "Context: {context}\nTone: {tone}\nLanguage: {lang}\nCount: {count}")
    ])
    chain = prompt | tool
    req = state["req"]
    over = max(req.count * 2, req.count + 6)
    res = await chain.ainvoke({"context": req.context, "tone": req.tone, "lang": req.language, "count": over})
    filtered = top_unique(res.ctas, max_items=req.count, max_chars=24)
    state["resp"] = CtaResponse(ctas=filtered)
    return state


def build_cta_graph():
    wf = StateGraph(CTAState)
    wf.add_node("draft", draft_ctas)
    wf.set_entry_point("draft")
    wf.add_edge("draft", END)
    return wf.compile()


cta_graph = build_cta_graph()


async def run_cta(req_dict: dict) -> dict:
    logger.info("--- Running CTA Agent ---")
    try:
        req = CtaRequest(**req_dict)
        init: CTAState = {"req": req, "resp": None, "error": None}
        final = await cta_graph.ainvoke(init)
        if final.get("error"):
            return {"error": final["error"]}
        return final["resp"].model_dump()
    except Exception as e:
        logger.error(f"[cta] critical error: {e}", exc_info=True)
        return {"error": "A critical error occurred while generating CTAs."}

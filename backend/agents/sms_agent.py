import logging
from typing import TypedDict

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_ollama.chat_models import ChatOllama
from langgraph.graph import StateGraph, END

from services.registry import get_services
from schemas.asset_schemas import SMSRequest, SMSResponse
from .utils.postprocess import clamp_length, dedupe_preserve_order
from .utils.policies import SMS


logger = logging.getLogger(__name__)


class SMSState(TypedDict):
    req: SMSRequest
    resp: SMSResponse | None
    error: str | None


class SMSTool(BaseModel):
    variants: list[str] = Field(default_factory=list)


def _llm() -> ChatOllama:
    try:
        return get_services().llm_fast
    except Exception:
        return ChatOllama(model="gemma3:1b", temperature=0.0)


async def draft_sms(state: SMSState) -> SMSState:
    logger.info("[sms] ▶ drafting sms variants …")
    tool = _llm().with_structured_output(SMSTool)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Generate short SMS variants (<=160 chars). Natural, clear CTA, no spammy all caps."),
        ("human", "Offer: {offer}\nTone: {tone}\nLanguage: {lang}\nCount: {count}")
    ])
    chain = prompt | tool
    req = state["req"]
    over = max(req.count * 2, req.count + 6)
    res = await chain.ainvoke({"offer": req.offer, "tone": req.tone, "lang": req.language, "count": over})
    variants = [clamp_length(v, SMS["variant_max"]) for v in res.variants]
    variants = dedupe_preserve_order([v for v in variants if v.strip()])[: req.count]
    state["resp"] = SMSResponse(variants=variants)
    return state


def build_sms_graph():
    wf = StateGraph(SMSState)
    wf.add_node("draft", draft_sms)
    wf.set_entry_point("draft")
    wf.add_edge("draft", END)
    return wf.compile()


sms_graph = build_sms_graph()


async def run_sms(req_dict: dict) -> dict:
    logger.info("--- Running SMS Agent ---")
    try:
        req = SMSRequest(**req_dict)
        init: SMSState = {"req": req, "resp": None, "error": None}
        final = await sms_graph.ainvoke(init)
        if final.get("error"):
            return {"error": final["error"]}
        return final["resp"].model_dump()
    except Exception as e:
        logger.error(f"[sms] critical error: {e}", exc_info=True)
        return {"error": "A critical error occurred while generating SMS variants."}

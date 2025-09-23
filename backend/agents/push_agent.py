import logging
from typing import TypedDict

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel
from langchain_ollama.chat_models import ChatOllama
from langgraph.graph import StateGraph, END

from services.registry import get_services
from schemas.asset_schemas import PushRequest, PushResponse
from .utils.postprocess import clamp_length
from .utils.policies import PUSH


logger = logging.getLogger(__name__)


class PushState(TypedDict):
    req: PushRequest
    resp: PushResponse | None
    error: str | None


class PushTool(BaseModel):
    title: str
    body: str
    cta: str


def _llm() -> ChatOllama:
    try:
        return get_services().llm_fast
    except Exception:
        return ChatOllama(model="gemma3:1b", temperature=0.0)


async def draft_push(state: PushState) -> PushState:
    logger.info("[push] ▶ drafting push notification …")
    tool = _llm().with_structured_output(PushTool)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Craft a concise push notification (title <= 40 chars, body <= 80 chars) with a strong CTA."),
        ("human", "Purpose: {purpose}\nChannel: {channel}\nTone: {tone}\nLanguage: {lang}")
    ])
    chain = prompt | tool
    req = state["req"]
    res = await chain.ainvoke({"purpose": req.message_purpose, "channel": req.channel, "tone": req.tone, "lang": req.language})
    title = clamp_length(res.title or "", PUSH["title_max"]) if res.title else ""
    body = clamp_length(res.body or "", PUSH["body_max"]) if res.body else ""
    cta = clamp_length(res.cta or "", PUSH["cta_max"]) if res.cta else ""
    state["resp"] = PushResponse(title=title, body=body, cta=cta)
    return state


def build_push_graph():
    wf = StateGraph(PushState)
    wf.add_node("draft", draft_push)
    wf.set_entry_point("draft")
    wf.add_edge("draft", END)
    return wf.compile()


push_graph = build_push_graph()


async def run_push(req_dict: dict) -> dict:
    logger.info("--- Running Push Agent ---")
    try:
        req = PushRequest(**req_dict)
        init: PushState = {"req": req, "resp": None, "error": None}
        final = await push_graph.ainvoke(init)
        if final.get("error"):
            return {"error": final["error"]}
        return final["resp"].model_dump()
    except Exception as e:
        logger.error(f"[push] critical error: {e}", exc_info=True)
        return {"error": "A critical error occurred while generating the push notification."}

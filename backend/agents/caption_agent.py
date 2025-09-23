import logging
from typing import TypedDict

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_ollama.chat_models import ChatOllama
from langgraph.graph import StateGraph, END

from services.registry import get_services
from schemas.asset_schemas import CaptionRequest, CaptionResponse
from .utils.postprocess import dedupe_preserve_order


logger = logging.getLogger(__name__)


class CAPState(TypedDict):
    req: CaptionRequest
    resp: CaptionResponse | None
    error: str | None


class CAPTool(BaseModel):
    captions: list[str] = Field(default_factory=list)


def _llm() -> ChatOllama:
    try:
        return get_services().llm_fast
    except Exception:
        return ChatOllama(model="gemma3:1b", temperature=0.0)


async def draft_captions(state: CAPState) -> CAPState:
    logger.info("[captions] ▶ drafting captions …")
    tool = _llm().with_structured_output(CAPTool)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Create platform-appropriate captions; short, engaging, with a soft CTA; avoid spam."),
        ("human", "Topic: {topic}\nPlatform: {platform}\nTone: {tone}\nLanguage: {lang}\nCount: {count}")
    ])
    chain = prompt | tool
    req = state["req"]
    over = max(req.count * 2, req.count + 10)
    res = await chain.ainvoke({"topic": req.topic, "platform": req.platform, "tone": req.tone, "lang": req.language, "count": over})
    caps = [c.strip() for c in res.captions if c.strip()]
    caps = dedupe_preserve_order(caps)[: req.count]
    state["resp"] = CaptionResponse(captions=caps)
    return state


def build_caption_graph():
    wf = StateGraph(CAPState)
    wf.add_node("draft", draft_captions)
    wf.set_entry_point("draft")
    wf.add_edge("draft", END)
    return wf.compile()


caption_graph = build_caption_graph()


async def run_caption(req_dict: dict) -> dict:
    logger.info("--- Running Caption Agent ---")
    try:
        req = CaptionRequest(**req_dict)
        init: CAPState = {"req": req, "resp": None, "error": None}
        final = await caption_graph.ainvoke(init)
        if final.get("error"):
            return {"error": final["error"]}
        return final["resp"].model_dump()
    except Exception as e:
        logger.error(f"[captions] critical error: {e}", exc_info=True)
        return {"error": "A critical error occurred while generating captions."}

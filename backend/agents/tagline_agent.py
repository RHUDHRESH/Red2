import logging
from typing import TypedDict

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_ollama.chat_models import ChatOllama
from langgraph.graph import StateGraph, END

from services.registry import get_services
from schemas.asset_schemas import TaglineRequest, TaglineResponse
from .utils.postprocess import top_unique
from .utils.policies import TAGLINE_MAX


logger = logging.getLogger(__name__)


class TLState(TypedDict):
    req: TaglineRequest
    resp: TaglineResponse | None
    error: str | None


class TLTool(BaseModel):
    taglines: list[str] = Field(default_factory=list)


def _llm() -> ChatOllama:
    try:
        return get_services().llm_fast
    except Exception:
        return ChatOllama(model="gemma3:1b", temperature=0.0)


async def draft_taglines(state: TLState) -> TLState:
    logger.info("[tagline] ▶ drafting taglines …")
    tool = _llm().with_structured_output(TLTool)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Generate 1-line taglines. Distinctive, believable, under 6 words where possible."),
        ("human", "Product summary: {summary}\nTone: {tone}\nLanguage: {lang}\nCount: {count}")
    ])
    chain = prompt | tool
    req = state["req"]
    over = max(req.count * 2, req.count + 10)
    res = await chain.ainvoke({"summary": req.product_summary, "tone": req.tone, "lang": req.language, "count": over})
    filtered = top_unique(res.taglines, max_items=req.count, max_chars=TAGLINE_MAX)
    state["resp"] = TaglineResponse(taglines=filtered)
    return state


def build_tagline_graph():
    wf = StateGraph(TLState)
    wf.add_node("draft", draft_taglines)
    wf.set_entry_point("draft")
    wf.add_edge("draft", END)
    return wf.compile()


tagline_graph = build_tagline_graph()


async def run_tagline(req_dict: dict) -> dict:
    logger.info("--- Running Tagline Agent ---")
    try:
        req = TaglineRequest(**req_dict)
        init: TLState = {"req": req, "resp": None, "error": None}
        final = await tagline_graph.ainvoke(init)
        if final.get("error"):
            return {"error": final["error"]}
        return final["resp"].model_dump()
    except Exception as e:
        logger.error(f"[tagline] critical error: {e}", exc_info=True)
        return {"error": "A critical error occurred while generating taglines."}

import logging
from typing import TypedDict

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_ollama.chat_models import ChatOllama
from langgraph.graph import StateGraph, END

from services.registry import get_services
from schemas.asset_schemas import HookRequest, HookResponse
from .utils.postprocess import top_unique


logger = logging.getLogger(__name__)


class HKState(TypedDict):
    req: HookRequest
    resp: HookResponse | None
    error: str | None


class HKTool(BaseModel):
    hooks: list[str] = Field(default_factory=list)


def _llm() -> ChatOllama:
    try:
        return get_services().llm_fast
    except Exception:
        return ChatOllama(model="gemma3:1b", temperature=0.0)


async def draft_hooks(state: HKState) -> HKState:
    logger.info("[hooks] ▶ drafting hooks …")
    tool = _llm().with_structured_output(HKTool)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Generate short, punchy hooks for short-form videos; curiosity gap or benefit-forward; <=80 chars."),
        ("human", "Topic: {topic}\nTone: {tone}\nLanguage: {lang}\nCount: {count}")
    ])
    chain = prompt | tool
    req = state["req"]
    over = max(req.count * 2, req.count + 10)
    res = await chain.ainvoke({"topic": req.topic, "tone": req.tone, "lang": req.language, "count": over})
    filtered = top_unique(res.hooks, max_items=req.count, max_chars=80)
    state["resp"] = HookResponse(hooks=filtered)
    return state


def build_hook_graph():
    wf = StateGraph(HKState)
    wf.add_node("draft", draft_hooks)
    wf.set_entry_point("draft")
    wf.add_edge("draft", END)
    return wf.compile()


hook_graph = build_hook_graph()


async def run_hook(req_dict: dict) -> dict:
    logger.info("--- Running Hook Agent ---")
    try:
        req = HookRequest(**req_dict)
        init: HKState = {"req": req, "resp": None, "error": None}
        final = await hook_graph.ainvoke(init)
        if final.get("error"):
            return {"error": final["error"]}
        return final["resp"].model_dump()
    except Exception as e:
        logger.error(f"[hooks] critical error: {e}", exc_info=True)
        return {"error": "A critical error occurred while generating hooks."}

import logging
from typing import TypedDict

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_ollama.chat_models import ChatOllama
from langgraph.graph import StateGraph, END

from services.registry import get_services
from schemas.asset_schemas import ThreadRequest, ThreadResponse


logger = logging.getLogger(__name__)


class ThState(TypedDict):
    req: ThreadRequest
    resp: ThreadResponse | None
    error: str | None


class ThTool(BaseModel):
    items: list[str] = Field(default_factory=list)


def _llm() -> ChatOllama:
    try:
        return get_services().llm_reasoning
    except Exception:
        return ChatOllama(model="gemma3:4b", temperature=0.3)


async def draft_thread(state: ThState) -> ThState:
    logger.info("[thread] ▶ drafting thread …")
    tool = _llm().with_structured_output(ThTool)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Create a platform-appropriate thread with concise posts that build on each other; keep each under ~280 chars."),
        ("human", "Topic: {topic}\nPlatform: {platform}\nPosts: {n}\nTone: {tone}\nLanguage: {lang}")
    ])
    chain = prompt | tool
    req = state["req"]
    res = await chain.ainvoke({"topic": req.topic, "platform": req.platform, "n": req.posts, "tone": req.tone, "lang": req.language})
    state["resp"] = ThreadResponse(platform=req.platform, items=res.items[: req.posts])
    return state


def build_thread_graph():
    wf = StateGraph(ThState)
    wf.add_node("draft", draft_thread)
    wf.set_entry_point("draft")
    wf.add_edge("draft", END)
    return wf.compile()


thread_graph = build_thread_graph()


async def run_thread(req_dict: dict) -> dict:
    logger.info("--- Running Thread Agent ---")
    try:
        req = ThreadRequest(**req_dict)
        init: ThState = {"req": req, "resp": None, "error": None}
        final = await thread_graph.ainvoke(init)
        if final.get("error"):
            return {"error": final["error"]}
        return final["resp"].model_dump()
    except Exception as e:
        logger.error(f"[thread] critical error: {e}", exc_info=True)
        return {"error": "A critical error occurred while generating the thread."}


import logging
from typing import TypedDict, List

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_ollama.chat_models import ChatOllama
from langgraph.graph import StateGraph, END

from services.registry import get_services
from schemas.asset_schemas import PollRequest, PollResponse, PollItem


logger = logging.getLogger(__name__)


class PollState(TypedDict):
    req: PollRequest
    resp: PollResponse | None
    error: str | None


class PollTool(BaseModel):
    polls: List[PollItem] = Field(default_factory=list)


def _llm() -> ChatOllama:
    try:
        return get_services().llm_fast
    except Exception:
        return ChatOllama(model="gemma3:1b", temperature=0.0)


async def draft_polls(state: PollState) -> PollState:
    logger.info("[poll] ▶ drafting polls …")
    tool = _llm().with_structured_output(PollTool)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Create short, engaging poll questions with 3-4 mutually exclusive options; no leading phrasing."),
        ("human", "Topic: {topic}\nPlatform: {platform}\nLanguage: {lang}\nCount: {count}")
    ])
    chain = prompt | tool
    req = state["req"]
    res = await chain.ainvoke({"topic": req.topic, "platform": req.platform, "lang": req.language, "count": req.count})
    state["resp"] = PollResponse(polls=res.polls[: req.count])
    return state


def build_poll_graph():
    wf = StateGraph(PollState)
    wf.add_node("draft", draft_polls)
    wf.set_entry_point("draft")
    wf.add_edge("draft", END)
    return wf.compile()


poll_graph = build_poll_graph()


async def run_poll(req_dict: dict) -> dict:
    logger.info("--- Running Poll Agent ---")
    try:
        req = PollRequest(**req_dict)
        init: PollState = {"req": req, "resp": None, "error": None}
        final = await poll_graph.ainvoke(init)
        if final.get("error"):
            return {"error": final["error"]}
        return final["resp"].model_dump()
    except Exception as e:
        logger.error(f"[poll] critical error: {e}", exc_info=True)
        return {"error": "A critical error occurred while generating polls."}


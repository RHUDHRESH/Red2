import logging
from typing import TypedDict

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_ollama.chat_models import ChatOllama
from langgraph.graph import StateGraph, END

from services.registry import get_services
from schemas.asset_schemas import HeadlineRequest, HeadlineResponse
from .utils.postprocess import top_unique


logger = logging.getLogger(__name__)


class HLState(TypedDict):
    req: HeadlineRequest
    resp: HeadlineResponse | None
    error: str | None


class HLTool(BaseModel):
    headlines: list[str] = Field(default_factory=list)


def _llm() -> ChatOllama:
    try:
        return get_services().llm_fast
    except Exception:
        return ChatOllama(model="gemma3:1b", temperature=0.0)


async def draft_headlines(state: HLState) -> HLState:
    logger.info("[headline] ▶ drafting headlines …")
    tool = _llm().with_structured_output(HLTool)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Generate concise, clicky headlines. Avoid clickbait; keep < 70 chars, unique, and on-topic."),
        ("human", "Topic: {topic}\nTone: {tone}\nLanguage: {lang}\nCount: {count}")
    ])
    chain = prompt | tool
    req = state["req"]
    over = max(req.count * 2, req.count + 10)
    res = await chain.ainvoke({"topic": req.topic, "tone": req.tone, "lang": req.language, "count": over})
    filtered = top_unique(res.headlines, max_items=req.count, max_chars=70)
    state["resp"] = HeadlineResponse(headlines=filtered)
    return state


def build_headline_graph():
    wf = StateGraph(HLState)
    wf.add_node("draft", draft_headlines)
    wf.set_entry_point("draft")
    wf.add_edge("draft", END)
    return wf.compile()


headline_graph = build_headline_graph()


async def run_headline(req_dict: dict) -> dict:
    logger.info("--- Running Headline Agent ---")
    try:
        req = HeadlineRequest(**req_dict)
        init: HLState = {"req": req, "resp": None, "error": None}
        final = await headline_graph.ainvoke(init)
        if final.get("error"):
            return {"error": final["error"]}
        return final["resp"].model_dump()
    except Exception as e:
        logger.error(f"[headline] critical error: {e}", exc_info=True)
        return {"error": "A critical error occurred while generating headlines."}

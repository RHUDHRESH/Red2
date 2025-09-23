import logging
from typing import TypedDict

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_ollama.chat_models import ChatOllama
from langgraph.graph import StateGraph, END

from services.registry import get_services
from schemas.asset_schemas import HashtagRequest, HashtagResponse
from .utils.postprocess import dedupe_preserve_order, sanitize_hashtag


logger = logging.getLogger(__name__)


class HTState(TypedDict):
    req: HashtagRequest
    resp: HashtagResponse | None
    error: str | None


class HTTool(BaseModel):
    hashtags: list[str] = Field(default_factory=list)


def _llm() -> ChatOllama:
    try:
        return get_services().llm_fast
    except Exception:
        return ChatOllama(model="gemma3:1b", temperature=0.0)


async def draft_hashtags(state: HTState) -> HTState:
    logger.info("[hashtags] ▶ drafting hashtags …")
    tool = _llm().with_structured_output(HTTool)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Generate platform-appropriate hashtags; lowercase, no spaces. Avoid banned or generic-only tags."),
        ("human", "Topic: {topic}\nPlatform: {platform}\nLanguage: {lang}\nCount: {count}")
    ])
    chain = prompt | tool
    req = state["req"]
    over = max(req.count * 2, req.count + 10)
    res = await chain.ainvoke({"topic": req.topic, "platform": req.platform, "lang": req.language, "count": over})
    tags = [sanitize_hashtag(h) for h in res.hashtags]
    tags = [t for t in tags if len(t) <= 30 and t != "#"]
    tags = dedupe_preserve_order(tags)[: req.count]
    state["resp"] = HashtagResponse(hashtags=tags)
    return state


def build_hashtag_graph():
    wf = StateGraph(HTState)
    wf.add_node("draft", draft_hashtags)
    wf.set_entry_point("draft")
    wf.add_edge("draft", END)
    return wf.compile()


hashtag_graph = build_hashtag_graph()


async def run_hashtag(req_dict: dict) -> dict:
    logger.info("--- Running Hashtag Agent ---")
    try:
        req = HashtagRequest(**req_dict)
        init: HTState = {"req": req, "resp": None, "error": None}
        final = await hashtag_graph.ainvoke(init)
        if final.get("error"):
            return {"error": final["error"]}
        return final["resp"].model_dump()
    except Exception as e:
        logger.error(f"[hashtags] critical error: {e}", exc_info=True)
        return {"error": "A critical error occurred while generating hashtags."}

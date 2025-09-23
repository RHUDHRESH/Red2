import logging
from typing import TypedDict

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel
from langchain_ollama.chat_models import ChatOllama
from langgraph.graph import StateGraph, END

from services.registry import get_services
from schemas.asset_schemas import PressReleaseRequest, PressReleaseResponse


logger = logging.getLogger(__name__)


class PRState(TypedDict):
    req: PressReleaseRequest
    resp: PressReleaseResponse | None
    error: str | None


class PRTool(BaseModel):
    headline: str
    subheadline: str
    body: str


def _llm() -> ChatOllama:
    try:
        return get_services().llm_reasoning
    except Exception:
        return ChatOllama(model="gemma3:4b", temperature=0.3)


async def draft_press_release(state: PRState) -> PRState:
    logger.info("[press] ▶ drafting press release …")
    tool = _llm().with_structured_output(PRTool)
    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a PR writer. Draft a standard press release (headline, subheadline, body) in journalistic tone with quotes if provided."),
        ("human",
         "Company: {company}\nAnnouncement: {announcement}\nDate: {date}\nQuotes: {quotes}\nLanguage: {lang}")
    ])
    chain = prompt | tool
    req = state["req"]
    res = await chain.ainvoke({"company": req.company, "announcement": req.announcement, "date": req.date_str, "quotes": " | ".join(req.quotes), "lang": req.language})
    state["resp"] = PressReleaseResponse(headline=res.headline, subheadline=res.subheadline, body=res.body)
    return state


def build_press_graph():
    wf = StateGraph(PRState)
    wf.add_node("draft", draft_press_release)
    wf.set_entry_point("draft")
    wf.add_edge("draft", END)
    return wf.compile()


press_graph = build_press_graph()


async def run_press_release(req_dict: dict) -> dict:
    logger.info("--- Running Press Release Agent ---")
    try:
        req = PressReleaseRequest(**req_dict)
        init: PRState = {"req": req, "resp": None, "error": None}
        final = await press_graph.ainvoke(init)
        if final.get("error"):
            return {"error": final["error"]}
        return final["resp"].model_dump()
    except Exception as e:
        logger.error(f"[press] critical error: {e}", exc_info=True)
        return {"error": "A critical error occurred while generating the press release."}


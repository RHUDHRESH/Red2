import logging
from typing import TypedDict, List

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_ollama.chat_models import ChatOllama
from langgraph.graph import StateGraph, END

from services.registry import get_services
from schemas.asset_schemas import NewsletterRequest, NewsletterResponse, NewsletterSection


logger = logging.getLogger(__name__)


class NLState(TypedDict):
    req: NewsletterRequest
    resp: NewsletterResponse | None
    error: str | None


class NLTool(BaseModel):
    title: str
    sections: List[NewsletterSection] = Field(default_factory=list)


def _llm() -> ChatOllama:
    try:
        return get_services().llm_reasoning
    except Exception:
        return ChatOllama(model="gemma3:4b", temperature=0.3)


async def draft_newsletter(state: NLState) -> NLState:
    logger.info("[newsletter] ▶ drafting newsletter outline …")
    tool = _llm().with_structured_output(NLTool)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Draft a concise newsletter issue outline with 3-6 sections, each with 3-5 bullets."),
        ("human", "Topic: {topic}\nSections: {n}\nTone: {tone}\nLanguage: {lang}")
    ])
    chain = prompt | tool
    req = state["req"]
    res = await chain.ainvoke({"topic": req.topic, "n": req.sections, "tone": req.tone, "lang": req.language})
    state["resp"] = NewsletterResponse(title=res.title, sections=res.sections[: req.sections])
    return state


def build_newsletter_graph():
    wf = StateGraph(NLState)
    wf.add_node("draft", draft_newsletter)
    wf.set_entry_point("draft")
    wf.add_edge("draft", END)
    return wf.compile()


newsletter_graph = build_newsletter_graph()


async def run_newsletter(req_dict: dict) -> dict:
    logger.info("--- Running Newsletter Agent ---")
    try:
        req = NewsletterRequest(**req_dict)
        init: NLState = {"req": req, "resp": None, "error": None}
        final = await newsletter_graph.ainvoke(init)
        if final.get("error"):
            return {"error": final["error"]}
        return final["resp"].model_dump()
    except Exception as e:
        logger.error(f"[newsletter] critical error: {e}", exc_info=True)
        return {"error": "A critical error occurred while generating the newsletter outline."}


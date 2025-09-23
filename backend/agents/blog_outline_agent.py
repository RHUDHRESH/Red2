import logging
from typing import TypedDict, List

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_ollama.chat_models import ChatOllama
from langgraph.graph import StateGraph, END

from services.registry import get_services
from schemas.asset_schemas import BlogOutlineRequest, BlogOutlineResponse, BlogSection


logger = logging.getLogger(__name__)


class BlogState(TypedDict):
    req: BlogOutlineRequest
    resp: BlogOutlineResponse | None
    error: str | None


class BlogTool(BaseModel):
    title: str
    sections: List[BlogSection] = Field(default_factory=list)


def _llm() -> ChatOllama:
    try:
        return get_services().llm_reasoning
    except Exception:
        return ChatOllama(model="gemma3:4b", temperature=0.3)


async def draft_outline(state: BlogState) -> BlogState:
    logger.info("[blog] ▶ drafting outline …")
    tool = _llm().with_structured_output(BlogTool)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Create a comprehensive but concise blog outline with section headings and 3-5 bullet talking points each."),
        ("human", "Topic: {topic}\nAudience: {aud}\nLanguage: {lang}\nTone: {tone}")
    ])
    chain = prompt | tool
    req = state["req"]
    res = await chain.ainvoke({"topic": req.topic, "aud": req.audience, "lang": req.language, "tone": req.tone})
    state["resp"] = BlogOutlineResponse(title=res.title, sections=res.sections)
    return state


def build_blog_graph():
    wf = StateGraph(BlogState)
    wf.add_node("draft", draft_outline)
    wf.set_entry_point("draft")
    wf.add_edge("draft", END)
    return wf.compile()


blog_graph = build_blog_graph()


async def run_blog_outline(req_dict: dict) -> dict:
    logger.info("--- Running Blog Outline Agent ---")
    try:
        req = BlogOutlineRequest(**req_dict)
        init: BlogState = {"req": req, "resp": None, "error": None}
        final = await blog_graph.ainvoke(init)
        if final.get("error"):
            return {"error": final["error"]}
        return final["resp"].model_dump()
    except Exception as e:
        logger.error(f"[blog] critical error: {e}", exc_info=True)
        return {"error": "A critical error occurred while generating the blog outline."}


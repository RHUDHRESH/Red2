import logging
from typing import TypedDict

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_ollama.chat_models import ChatOllama
from langgraph.graph import StateGraph, END

from services.registry import get_services
from schemas.asset_schemas import TestimonialRequest, TestimonialResponse


logger = logging.getLogger(__name__)


class TSState(TypedDict):
    req: TestimonialRequest
    resp: TestimonialResponse | None
    error: str | None


class TSTool(BaseModel):
    quotes: list[str] = Field(default_factory=list)


def _llm() -> ChatOllama:
    try:
        return get_services().llm_reasoning
    except Exception:
        return ChatOllama(model="gemma3:4b", temperature=0.3)


async def draft_testimonials(state: TSState) -> TSState:
    logger.info("[testimonials] ▶ drafting quotes …")
    tool = _llm().with_structured_output(TSTool)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Generate authentic-sounding testimonial quotes (1-2 sentences) without exaggeration; include subtle specifics when possible."),
        ("human", "Product: {summary}\nPersonas: {personas}\nTone: {tone}\nLanguage: {lang}\nCount: {count}")
    ])
    chain = prompt | tool
    req = state["req"]
    res = await chain.ainvoke({
        "summary": req.product_summary,
        "personas": ", ".join(req.personas) if req.personas else "",
        "tone": req.tone,
        "lang": req.language,
        "count": req.count,
    })
    state["resp"] = TestimonialResponse(quotes=res.quotes[: req.count])
    return state


def build_testimonial_graph():
    wf = StateGraph(TSState)
    wf.add_node("draft", draft_testimonials)
    wf.set_entry_point("draft")
    wf.add_edge("draft", END)
    return wf.compile()


testimonial_graph = build_testimonial_graph()


async def run_testimonial(req_dict: dict) -> dict:
    logger.info("--- Running Testimonial Agent ---")
    try:
        req = TestimonialRequest(**req_dict)
        init: TSState = {"req": req, "resp": None, "error": None}
        final = await testimonial_graph.ainvoke(init)
        if final.get("error"):
            return {"error": final["error"]}
        return final["resp"].model_dump()
    except Exception as e:
        logger.error(f"[testimonials] critical error: {e}", exc_info=True)
        return {"error": "A critical error occurred while generating testimonials."}


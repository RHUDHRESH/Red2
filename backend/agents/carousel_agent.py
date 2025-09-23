import logging
from typing import TypedDict, List

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_ollama.chat_models import ChatOllama
from langgraph.graph import StateGraph, END

from services.registry import get_services
from schemas.asset_schemas import CarouselRequest, CarouselResponse, CarouselSlide


logger = logging.getLogger(__name__)


class CarouselState(TypedDict):
    req: CarouselRequest
    resp: CarouselResponse | None
    error: str | None


class SlidesTool(BaseModel):
    slides: List[CarouselSlide] = Field(default_factory=list)
    caption: str
    hashtags: List[str] = Field(default_factory=list)


def _llm() -> ChatOllama:
    try:
        return get_services().llm_reasoning
    except Exception:
        return ChatOllama(model="gemma3:4b", temperature=0.3)


async def draft_carousel(state: CarouselState) -> CarouselState:
    logger.info("[carousel] ▶ drafting slides …")
    tool = _llm().with_structured_output(SlidesTool)
    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a social content strategist. Create an Instagram/LinkedIn carousel outline with concise slides."
         " Each slide needs a heading and 3-5 bullets. Keep copy punchy and helpful. Include a caption and hashtags."),
        ("human",
         "Topic: {topic}\nAudience: {aud}\nSlides: {n}\nCTA: {cta}\nLanguage: {lang}\nTone: {tone}")
    ])
    req = state["req"]
    chain = prompt | tool
    res = await chain.ainvoke({
        "topic": req.topic,
        "aud": req.audience,
        "n": req.slides_count,
        "cta": req.call_to_action,
        "lang": req.language,
        "tone": req.tone,
    })
    slides = res.slides[: req.slides_count]
    hashtags = [h if h.startswith("#") else f"#{h}" for h in res.hashtags][:12]
    state["resp"] = CarouselResponse(slides=slides, caption=res.caption, hashtags=hashtags)
    return state


def build_carousel_graph():
    wf = StateGraph(CarouselState)
    wf.add_node("draft", draft_carousel)
    wf.set_entry_point("draft")
    wf.add_edge("draft", END)
    return wf.compile()


carousel_graph = build_carousel_graph()


async def run_carousel(req_dict: dict) -> dict:
    logger.info("--- Running Carousel Agent ---")
    try:
        req = CarouselRequest(**req_dict)
        init: CarouselState = {"req": req, "resp": None, "error": None}
        final = await carousel_graph.ainvoke(init)
        if final.get("error"):
            return {"error": final["error"]}
        return final["resp"].model_dump()
    except Exception as e:
        logger.error(f"[carousel] critical error: {e}", exc_info=True)
        return {"error": "A critical error occurred while generating the carousel."}


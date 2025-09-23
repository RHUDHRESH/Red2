import logging
from typing import TypedDict

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_ollama.chat_models import ChatOllama
from langgraph.graph import StateGraph, END

from services.registry import get_services
from schemas.asset_schemas import MemeRequest, MemeResponse


logger = logging.getLogger(__name__)


class MemeState(TypedDict):
    req: MemeRequest
    meme: MemeResponse | None
    error: str | None


class MemeTool(BaseModel):
    template_name: str
    top_text: str
    bottom_text: str
    alt_text: str
    caption: str
    hashtags: list[str] = Field(default_factory=list)


def _llm() -> ChatOllama:
    try:
        return get_services().llm_reasoning
    except Exception:
        return ChatOllama(model="gemma3:4b", temperature=0.4)


async def draft_meme(state: MemeState) -> MemeState:
    logger.info("[meme] ▶ drafting meme …")
    tool = _llm().with_structured_output(MemeTool)
    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a creative meme director. Given a topic, audience, and style, propose a meme template and overlay text (top/bottom)."
         " Keep it punchy, avoid offensive content, and ensure it works without an image if needed (use alt_text). Include 5-10 hashtags."),
        ("human",
         "Topic: {topic}\nAudience: {aud}\nStyle: {style}\nTone: {tone}\nLanguage: {lang}")
    ])
    chain = prompt | tool
    req = state["req"]
    res = await chain.ainvoke({
        "topic": req.topic,
        "aud": req.audience,
        "style": req.style,
        "tone": req.tone,
        "lang": req.language,
    })
    meme = MemeResponse(
        template_name=res.template_name,
        top_text=res.top_text,
        bottom_text=res.bottom_text,
        alt_text=res.alt_text,
        caption=res.caption,
        hashtags=[h if h.startswith("#") else f"#{h}" for h in res.hashtags][:10],
    )
    state["meme"] = meme
    return state


def build_meme_graph():
    wf = StateGraph(MemeState)
    wf.add_node("draft", draft_meme)
    wf.set_entry_point("draft")
    wf.add_edge("draft", END)
    return wf.compile()


meme_graph = build_meme_graph()


async def run_meme(req_dict: dict) -> dict:
    logger.info("--- Running Meme Agent ---")
    try:
        req = MemeRequest(**req_dict)
        init: MemeState = {"req": req, "meme": None, "error": None}
        final = await meme_graph.ainvoke(init)
        if final.get("error"):
            return {"error": final["error"]}
        return final["meme"].model_dump()
    except Exception as e:
        logger.error(f"[meme] critical error: {e}", exc_info=True)
        return {"error": "A critical error occurred while generating the meme."}


import logging
from typing import TypedDict, List

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_ollama.chat_models import ChatOllama
from langgraph.graph import StateGraph, END

from services.registry import get_services
from schemas.asset_schemas import ShortVideoRequest, ShortVideoResponse, VideoBeat


logger = logging.getLogger(__name__)


class VideoState(TypedDict):
    req: ShortVideoRequest
    resp: ShortVideoResponse | None
    error: str | None


class BeatsTool(BaseModel):
    hook: str
    beats: List[VideoBeat] = Field(default_factory=list)
    voiceover_script: str
    caption: str
    hashtags: List[str] = Field(default_factory=list)


def _llm() -> ChatOllama:
    try:
        return get_services().llm_reasoning
    except Exception:
        return ChatOllama(model="gemma3:4b", temperature=0.3)


async def draft_video(state: VideoState) -> VideoState:
    logger.info("[video] ▶ drafting short video …")
    tool = _llm().with_structured_output(BeatsTool)
    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a short-form video director. Create a tight script with a strong hook, beat-by-beat plan, on-screen text, and a VO script."
         " Keep within duration. Include caption and hashtags."),
        ("human",
         "Topic: {topic}\nPlatform: {platform}\nDuration: {dur}s\nLanguage: {lang}\nTone: {tone}")
    ])
    req = state["req"]
    chain = prompt | tool
    res = await chain.ainvoke({
        "topic": req.topic,
        "platform": req.platform,
        "dur": req.duration_seconds,
        "lang": req.language,
        "tone": req.tone,
    })
    hashtags = [h if h.startswith("#") else f"#{h}" for h in res.hashtags][:10]
    state["resp"] = ShortVideoResponse(hook=res.hook, beats=res.beats, voiceover_script=res.voiceover_script, caption=res.caption, hashtags=hashtags)
    return state


def build_short_video_graph():
    wf = StateGraph(VideoState)
    wf.add_node("draft", draft_video)
    wf.set_entry_point("draft")
    wf.add_edge("draft", END)
    return wf.compile()


short_video_graph = build_short_video_graph()


async def run_short_video(req_dict: dict) -> dict:
    logger.info("--- Running Short Video Agent ---")
    try:
        req = ShortVideoRequest(**req_dict)
        init: VideoState = {"req": req, "resp": None, "error": None}
        final = await short_video_graph.ainvoke(init)
        if final.get("error"):
            return {"error": final["error"]}
        return final["resp"].model_dump()
    except Exception as e:
        logger.error(f"[video] critical error: {e}", exc_info=True)
        return {"error": "A critical error occurred while generating the short video script."}


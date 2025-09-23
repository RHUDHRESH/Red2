import asyncio
import logging
from typing import TypedDict, Optional

from langgraph.graph import StateGraph, END

from services.registry import get_services
from schemas.asset_schemas import (
    SupervisorRequest,
    SupervisorResponse,
    MemeResponse,
    CarouselResponse,
    ShortVideoResponse,
    AdCopyResponse,
    ImagePromptResponse,
    ThreadResponse,
)
from agents.meme_agent import run_meme
from agents.carousel_agent import run_carousel
from agents.short_video_agent import run_short_video
from agents.deep_research_agent import run_deep_research
from agents.ad_copy_agent import run_ad_copy
from agents.image_prompt_agent import run_image_prompt
from agents.thread_agent import run_thread


logger = logging.getLogger(__name__)


class SupState(TypedDict):
    req: SupervisorRequest
    research_summary: Optional[str]
    meme: Optional[MemeResponse]
    carousel: Optional[CarouselResponse]
    short_video: Optional[ShortVideoResponse]
    ad_copy: Optional[AdCopyResponse]
    image_prompt: Optional[ImagePromptResponse]
    thread: Optional[ThreadResponse]
    error: Optional[str]


async def maybe_research(state: SupState) -> SupState:
    logger.info("[supervisor] ▶ considering research …")
    req = state["req"]
    if not req.research:
        return state
    # Run deep research for the topic and synthesize a short summary
    res = await run_deep_research({"query": req.topic, "max_results": 8, "max_pages": 6})
    if "error" in res:
        logger.warning(f"[supervisor] research failed: {res['error']}")
        return state
    # Shorten into a brief note using summarizer
    notes = []
    for f in res.get("findings", [])[:6]:
        st = f.get("statement") if isinstance(f, dict) else None
        if st:
            notes.append(f"• {st}")
    summary = "\n".join(notes)
    # Store to be passed as context to asset agents via services if needed
    state["research_summary"] = summary
    return state


async def generate_assets(state: SupState) -> SupState:
    logger.info("[supervisor] ▶ generating assets …")
    req = state["req"]
    tasks = []
    if "meme" in req.asset_types:
        tasks.append(run_meme({"topic": req.topic, "audience": req.audience, "tone": req.tone, "language": req.language}))
    else:
        tasks.append(asyncio.sleep(0, result=None))
    if "carousel" in req.asset_types:
        tasks.append(run_carousel({"topic": req.topic, "audience": req.audience, "language": req.language, "tone": req.tone, "slides_count": 7, "call_to_action": "Learn more"}))
    else:
        tasks.append(asyncio.sleep(0, result=None))
    if "short_video" in req.asset_types:
        tasks.append(run_short_video({"topic": req.topic, "platform": "instagram", "duration_seconds": 30, "language": req.language, "tone": req.tone}))
    else:
        tasks.append(asyncio.sleep(0, result=None))
    if "ad_copy" in req.asset_types:
        tasks.append(run_ad_copy({"product_summary": req.topic, "platforms": ["facebook","instagram"], "call_to_action": "Learn more", "language": req.language, "tone": req.tone}))
    else:
        tasks.append(asyncio.sleep(0, result=None))
    if "image_prompt" in req.asset_types:
        tasks.append(run_image_prompt({"concept": req.topic, "style": "cinematic", "brand_palette": [], "language": req.language}))
    else:
        tasks.append(asyncio.sleep(0, result=None))
    if "thread" in req.asset_types:
        tasks.append(run_thread({"topic": req.topic, "platform": "twitter", "posts": 8, "language": req.language, "tone": req.tone}))
    else:
        tasks.append(asyncio.sleep(0, result=None))

    results = await asyncio.gather(*tasks)
    # Assign if present and not error
    if results[0] and "error" not in results[0]:
        state["meme"] = MemeResponse(**results[0])
    if results[1] and "error" not in results[1]:
        state["carousel"] = CarouselResponse(**results[1])
    if results[2] and "error" not in results[2]:
        state["short_video"] = ShortVideoResponse(**results[2])
    if results[3] and "error" not in results[3]:
        state["ad_copy"] = AdCopyResponse(**results[3])
    if results[4] and "error" not in results[4]:
        state["image_prompt"] = ImagePromptResponse(**results[4])
    if results[5] and "error" not in results[5]:
        state["thread"] = ThreadResponse(**results[5])
    return state


async def moderate_assets(state: SupState) -> SupState:
    logger.info("[supervisor] ▶ moderating assets …")
    svc = get_services()
    # Combine texts and run moderation if available
    texts = []
    if state.get("meme"):
        m = state["meme"]
        texts.append(" ".join([m.caption, m.top_text, m.bottom_text]))
    if state.get("carousel"):
        c = state["carousel"]
        texts.append(c.caption + " " + " ".join([b for s in c.slides for b in s.bullets]))
    if state.get("short_video"):
        v = state["short_video"]
        texts.append(v.caption + " " + v.voiceover_script)
    if not texts:
        return state
    report = await svc.moderation.evaluate("\n".join(texts)[:6000])
    if not report.compliance_ok:
        logger.warning(f"[supervisor] moderation issues: {report.risk_level} {report.notes}")
    return state


def build_supervisor_graph():
    wf = StateGraph(SupState)
    wf.add_node("research", maybe_research)
    wf.add_node("generate", generate_assets)
    wf.add_node("moderate", moderate_assets)
    wf.set_entry_point("research")
    wf.add_edge("research", "generate")
    wf.add_edge("generate", "moderate")
    wf.add_edge("moderate", END)
    return wf.compile()


supervisor_graph = build_supervisor_graph()


async def run_asset_supervisor(req_dict: dict) -> dict:
    logger.info("--- Running Asset Supervisor Agent ---")
    try:
        req = SupervisorRequest(**req_dict)
        init: SupState = {"req": req, "research_summary": None, "meme": None, "carousel": None, "short_video": None, "ad_copy": None, "image_prompt": None, "thread": None, "error": None}
        final = await supervisor_graph.ainvoke(init)
        if final.get("error"):
            return {"error": final["error"]}
        return SupervisorResponse(
            topic=req.topic,
            research_summary=final.get("research_summary"),
            meme=final.get("meme"),
            carousel=final.get("carousel"),
            short_video=final.get("short_video"),
            ad_copy=final.get("ad_copy"),
            image_prompt=final.get("image_prompt"),
            thread=final.get("thread"),
        ).model_dump()
    except Exception as e:
        logger.error(f"[supervisor] critical error: {e}", exc_info=True)
        return {"error": "A critical error occurred while supervising asset creation."}

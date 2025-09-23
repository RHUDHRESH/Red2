import asyncio
import logging
from datetime import date, timedelta
from typing import TypedDict, List, Dict

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_ollama.chat_models import ChatOllama
from langgraph.graph import StateGraph, END

from services.registry import get_services
from schemas.social_calendar_schemas import SocialCalendarRequest, SocialCalendarResponse, SocialPostPlan


logger = logging.getLogger(__name__)


class CalState(TypedDict):
    req: SocialCalendarRequest
    themes: List[str]
    signals: Dict[str, str]  # theme -> notes
    posts: List[SocialPostPlan]
    error: str | None


class ThemesTool(BaseModel):
    themes: List[str] = Field(description="5-8 distinct content themes for the topic")


class PostIdea(BaseModel):
    platform: str
    theme: str
    idea: str
    caption: str
    hashtags: List[str] = Field(default_factory=list)


class IdeasTool(BaseModel):
    ideas: List[PostIdea] = Field(default_factory=list)


def _llm_fast() -> ChatOllama:
    try:
        return get_services().llm_fast
    except Exception:
        return ChatOllama(model="gemma3:1b", temperature=0.0)


def _llm_reason() -> ChatOllama:
    try:
        return get_services().llm_reasoning
    except Exception:
        return ChatOllama(model="gemma3:4b", temperature=0.3)


async def plan_themes(state: CalState) -> CalState:
    logger.info("[calendar] ▶ planning themes …")
    tool = _llm_fast().with_structured_output(ThemesTool)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Generate 5-8 crisp, non-overlapping content themes for the topic."),
        ("human", "Topic: {topic}\nAudience: local food customers in India")
    ])
    chain = prompt | tool
    res = await chain.ainvoke({"topic": state["req"].topic})
    state["themes"] = res.themes[:8]
    return state


async def gather_signals(state: CalState) -> CalState:
    logger.info("[calendar] ▶ gathering signals …")
    svc = get_services()
    signals: Dict[str, str] = {}
    sem = asyncio.Semaphore(3)

    async def _one(theme: str) -> None:
        async with sem:
            # Pull a few signals across sources
            tw, rd, yt, nw = await asyncio.gather(
                svc.twitter.search_recent(theme, max_results=5),
                svc.reddit.search(theme, limit=5),
                svc.youtube_search.search(theme, max_results=5),
                svc.news.search(theme, max_results=5),
            )
            snippets = []
            for t in tw or []:
                snippets.append(getattr(t, "text", ""))
            for r in rd or []:
                snippets.append(getattr(r, "title", ""))
            for v in yt or []:
                snippets.append(getattr(v, "title", ""))
            for n in nw or []:
                snippets.append(getattr(n, "title", ""))
            notes = await svc.summarizer.summarize("\n".join(snippets)[:3000], mode="brief") if snippets else ""
            signals[theme] = notes

    await asyncio.gather(*[_one(t) for t in state["themes"]])
    state["signals"] = signals
    return state


async def draft_ideas(state: CalState) -> CalState:
    logger.info("[calendar] ▶ drafting post ideas …")
    tool = _llm_reason().with_structured_output(IdeasTool)
    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a social content strategist. Given platforms, themes and signal notes, propose high-quality post ideas."
         " Output 1-2 ideas per theme per platform, with a short caption and 5-10 hashtags (lowercase, no spaces, prepend '#')."),
        ("human",
         "Platforms: {platforms}\nLanguage: {lang}\nThemes: {themes}\nSignal notes (JSON): {signals_json}")
    ])
    import json
    signals_json = json.dumps(state["signals"])
    chain = prompt | tool
    res = await chain.ainvoke({
        "platforms": ", ".join(state["req"].platforms),
        "lang": state["req"].language,
        "themes": ", ".join(state["themes"]),
        "signals_json": signals_json,
    })
    # Convert to post plans with placeholder dates for now; dates assigned later.
    ideas: List[SocialPostPlan] = []
    for idea in res.ideas:
        hashtags = [h if h.startswith("#") else f"#{h}" for h in idea.hashtags][:10]
        ideas.append(SocialPostPlan(platform=idea.platform, date="", theme=idea.theme, idea=idea.idea, caption=idea.caption, hashtags=hashtags))
    state["posts"] = ideas
    return state


async def schedule_posts(state: CalState) -> CalState:
    logger.info("[calendar] ▶ scheduling posts …")
    # Assign dates evenly across weeks and platforms
    req = state["req"]
    start = date.fromisoformat(req.start_date) if req.start_date else date.today()
    total_needed = req.weeks * req.posts_per_week
    # Filter ideas by selected platforms and cap to total_needed
    ideas = [p for p in state["posts"] if p.platform.lower() in {x.lower() for x in req.platforms}][: total_needed]
    scheduled: List[SocialPostPlan] = []
    if not ideas:
        state["posts"] = []
        return state
    day = start
    idx = 0
    while len(scheduled) < len(ideas):
        p = ideas[idx]
        scheduled.append(SocialPostPlan(**{**p.model_dump(), "date": day.isoformat()}))
        idx += 1
        day = day + timedelta(days=1)
        if idx >= len(ideas):
            break
    state["posts"] = scheduled
    return state


def build_social_calendar_graph():
    wf = StateGraph(CalState)
    # Node names must be distinct from state keys
    wf.add_node("themes_node", plan_themes)
    wf.add_node("signals_node", gather_signals)
    wf.add_node("ideas_node", draft_ideas)
    wf.add_node("schedule_node", schedule_posts)
    wf.set_entry_point("themes_node")
    wf.add_edge("themes_node", "signals_node")
    wf.add_edge("signals_node", "ideas_node")
    wf.add_edge("ideas_node", "schedule_node")
    wf.add_edge("schedule_node", END)
    return wf.compile()


social_calendar_graph = build_social_calendar_graph()


async def run_social_calendar(req_dict: dict) -> dict:
    logger.info("--- Running Social Calendar Agent ---")
    try:
        req = SocialCalendarRequest(**req_dict)
        init: CalState = {"req": req, "themes": [], "signals": {}, "posts": [], "error": None}
        final = await social_calendar_graph.ainvoke(init)
        if final.get("error"):
            return {"error": final["error"]}
        start_date = req.start_date or date.today().isoformat()
        return SocialCalendarResponse(topic=req.topic, start_date=start_date, weeks=req.weeks, posts=final["posts"]).model_dump()
    except Exception as e:
        logger.error(f"[calendar] critical error: {e}", exc_info=True)
        return {"error": "A critical error occurred while building the social calendar."}

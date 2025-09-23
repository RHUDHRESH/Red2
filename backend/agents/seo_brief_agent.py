import asyncio
import logging
from typing import TypedDict, List, Dict

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_ollama.chat_models import ChatOllama
from langgraph.graph import StateGraph, END

from services.registry import get_services
from schemas.seo_schemas import SEOBriefRequest, SEOBriefResponse, SEOSourceNote, SEOBrief, OutlineSection


logger = logging.getLogger(__name__)


class SEOState(TypedDict):
    req: SEOBriefRequest
    candidates: List[Dict]
    notes: List[SEOSourceNote]
    brief: SEOBrief | None
    error: str | None


class BriefTool(BaseModel):
    meta_title: str
    meta_description: str
    primary_keyword: str
    secondary_keywords: List[str] = Field(default_factory=list)
    outline: List[OutlineSection] = Field(default_factory=list)
    faqs: List[str] = Field(default_factory=list)


def _llm() -> ChatOllama:
    try:
        return get_services().llm_reasoning
    except Exception:
        return ChatOllama(model="gemma3:4b", temperature=0.3)


async def collect_sources(state: SEOState) -> SEOState:
    logger.info("[seo] ▶ collecting sources …")
    svc = get_services()
    q = state["req"].topic
    per = max(3, min(state["req"].max_sources, 20))
    # Search across text + news + video previews
    tasks = [
        svc.search.search(q, max_results=per),
        svc.news.search(q, max_results=per) if hasattr(svc, "news") else asyncio.sleep(0, result=[]),
        svc.youtube_search.search(q, max_results=per) if hasattr(svc, "youtube_search") else asyncio.sleep(0, result=[]),
    ]
    results = await asyncio.gather(*tasks)
    # Normalize
    candidates: List[Dict] = []
    for item in state["req"].seed_urls:
        candidates.append({"title": "", "url": str(item), "snippet": ""})
    for group in results:
        for it in group or []:
            title = getattr(it, "title", "") if not isinstance(it, dict) else it.get("title", "")
            url = getattr(it, "url", "") if not isinstance(it, dict) else it.get("url", it.get("content", ""))
            snippet = getattr(it, "snippet", getattr(it, "body", "")) if not isinstance(it, dict) else it.get("snippet", it.get("body", ""))
            if url:
                candidates.append({"title": title, "url": url, "snippet": snippet})
    # Dedup and cap
    seen = set(); deduped = []
    for c in candidates:
        if c["url"] in seen:
            continue
        seen.add(c["url"])
        deduped.append(c)
    state["candidates"] = deduped[: state["req"].max_sources]
    logger.info(f"[seo] ✅ collected {len(state['candidates'])} sources")
    return state


async def note_sources(state: SEOState) -> SEOState:
    logger.info("[seo] ▶ fetching + noting sources …")
    svc = get_services()
    notes: List[SEOSourceNote] = []
    sem = asyncio.Semaphore(6)

    async def _one(c):
        async with sem:
            url = c["url"]
            preview = await svc.link_preview.fetch(url)
            text = await svc.scraper.scrape_text(url)
            summary = await svc.summarizer.summarize(text, mode="brief") if text else (preview.description or "")
            kws = await svc.keywords.extract(text, top_k=10) if text else []
            return SEOSourceNote(url=url, title=preview.title or c["title"], summary=summary, keywords=kws)

    notes = await asyncio.gather(*[_one(c) for c in state["candidates"]])
    state["notes"] = [n for n in notes if n]
    logger.info(f"[seo] ✅ created notes for {len(state['notes'])} sources")
    return state


async def synthesize_brief(state: SEOState) -> SEOState:
    logger.info("[seo] ▶ synthesizing SEO brief …")
    llm = _llm()
    tool = llm.with_structured_output(BriefTool)
    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are an expert SEO strategist. Given source notes (titles, summaries, keywords) for a topic, produce a high‑quality SEO brief.\n"
         "Keep meta title under ~60 chars; meta description under ~160 chars. List 6‑12 secondary keywords."
         ),
        ("human",
         "Topic: {topic}\nLanguage: {lang}\n\n"
         "Sources (JSON):\n{notes_json}")
    ])
    import json
    notes_json = json.dumps([n.model_dump() for n in state["notes"]])
    chain = prompt | tool
    res = await chain.ainvoke({"topic": state["req"].topic, "lang": state["req"].language, "notes_json": notes_json})
    # Build references list
    refs = [n.url for n in state["notes"]]
    state["brief"] = SEOBrief(
        meta_title=res.meta_title,
        meta_description=res.meta_description,
        primary_keyword=res.primary_keyword,
        secondary_keywords=res.secondary_keywords,
        outline=res.outline,
        faqs=res.faqs,
        references=refs,
    )
    return state


def build_seo_brief_graph():
    wf = StateGraph(SEOState)
    wf.add_node("collect", collect_sources)
    wf.add_node("note", note_sources)
    # Node name must not clash with state key names
    wf.add_node("brief_node", synthesize_brief)
    wf.set_entry_point("collect")
    wf.add_edge("collect", "note")
    wf.add_edge("note", "brief_node")
    wf.add_edge("brief_node", END)
    return wf.compile()


seo_brief_graph = build_seo_brief_graph()


async def run_seo_brief(req_dict: dict) -> dict:
    logger.info("--- Running SEO Brief Agent ---")
    try:
        req = SEOBriefRequest(**req_dict)
        init: SEOState = {"req": req, "candidates": [], "notes": [], "brief": None, "error": None}
        final = await seo_brief_graph.ainvoke(init)
        if final.get("error"):
            return {"error": final["error"]}
        return SEOBriefResponse(topic=req.topic, language=req.language, sources=final["notes"], brief=final["brief"]).model_dump()
    except Exception as e:
        logger.error(f"[seo] critical error: {e}", exc_info=True)
        return {"error": "A critical error occurred while generating the SEO brief."}

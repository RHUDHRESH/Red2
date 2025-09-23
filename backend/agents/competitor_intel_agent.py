import asyncio
import logging
from typing import TypedDict, List, Dict

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_ollama.chat_models import ChatOllama
from agents.utils.toolkit import bind_llm_with_tools
from langgraph.graph import StateGraph, END

from services.registry import get_services
from schemas.competitor_schemas import (
    CompetitorScanRequest,
    CompetitorScanResponse,
    CompetitorCard,
    CompetitorSignal,
)


logger = logging.getLogger(__name__)


class CIState(TypedDict):
    req: CompetitorScanRequest
    candidates: List[Dict]
    enriched: List[Dict]
    cards: List[CompetitorCard]
    error: str | None


class CardTool(BaseModel):
    name: str = Field(..., description="Competitor brand or product name")
    positioning: str = Field(..., description="Short summary of how they position themselves")
    description: str = Field(..., description="One paragraph describing their offering")
    keywords: List[str] = Field(default_factory=list, description="5-10 keywords")
    strength_score: float = Field(ge=0.0, le=1.0, default=0.6, description="Heuristic strength 0-1")


def _llm() -> ChatOllama:
    try:
        return get_services().llm_reasoning
    except Exception:
        return ChatOllama(model="gemma3:4b", temperature=0.3)


async def collect_candidates(state: CIState) -> CIState:
    logger.info("[competitors] ▶ collecting candidates …")
    svc = get_services()
    q = state["req"].query
    per = state["req"].per_source
    # Collect across a few channels
    tasks = [
        svc.search.search(q, max_results=per),
        svc.producthunt.search(q, max_results=per) if hasattr(svc, "producthunt") else asyncio.sleep(0, result=[]),
        svc.linkedin.search(q, max_results=per),
        svc.news.search(q, max_results=per),
        svc.youtube_search.search(q, max_results=per),
        svc.reddit.search(q, limit=per),
    ]
    results = await asyncio.gather(*tasks)
    candidates: List[Dict] = []
    for group in results:
        for item in group or []:
            # Normalize a few shapes to a common dict {title, url, snippet}
            if isinstance(item, dict):
                title = item.get("title") or item.get("name") or ""
                url = item.get("url") or item.get("href") or item.get("content") or ""
                snippet = item.get("snippet") or item.get("summary") or item.get("body") or ""
            else:
                title = getattr(item, "title", "")
                url = getattr(item, "url", "")
                snippet = getattr(item, "snippet", getattr(item, "text", ""))
            if url:
                candidates.append({"title": title, "url": url, "snippet": snippet})
    # De-dup by URL
    seen = set()
    deduped = []
    for c in candidates:
        if c["url"] in seen:
            continue
        seen.add(c["url"])
        deduped.append(c)
    state["candidates"] = deduped[: state["req"].max_candidates]
    logger.info(f"[competitors] ✅ collected {len(state['candidates'])} candidates")
    return state


async def enrich_candidates(state: CIState) -> CIState:
    logger.info("[competitors] ▶ enriching candidates …")
    svc = get_services()
    cands = state["candidates"]
    sem = asyncio.Semaphore(6)
    enriched: List[Dict] = []

    async def _one(c):
        async with sem:
            url = c["url"]
            preview = await svc.link_preview.fetch(url)
            text = await svc.scraper.scrape_text(url)
            # quick keywords
            kw = await svc.keywords.extract(text, top_k=10) if text else []
            return {
                "title": preview.title or c["title"],
                "url": url,
                "snippet": c["snippet"],
                "description": preview.description or "",
                "text": text[:3000] if text else "",
                "keywords": kw,
            }

    enriched = await asyncio.gather(*[_one(c) for c in cands])
    state["enriched"] = enriched
    logger.info(f"[competitors] ✅ enriched {len(enriched)} candidates")
    return state


async def draft_cards(state: CIState) -> CIState:
    logger.info("[competitors] ▶ drafting cards …")
    tool = bind_llm_with_tools(_llm(), ["extract_keywords", "summarize_text"]).with_structured_output(CardTool)
    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a market analyst. Based on a page title, description and body excerpt, synthesize a concise competitor card."
         " Be factual and avoid hype. Include positioning and 5-10 keywords. Score strength 0-1."),
        ("human", "Title: {title}\nDescription: {desc}\nKeywords: {kw}\nBody excerpt:\n{text}")
    ])
    chain = prompt | tool
    cards: List[CompetitorCard] = []
    for e in state["enriched"]:
        try:
            res = await chain.ainvoke({
                "title": e.get("title", ""),
                "desc": e.get("description", ""),
                "kw": ", ".join(e.get("keywords", [])),
                "text": e.get("text", ""),
            })
            cards.append(
                CompetitorCard(
                    name=res.name or (e.get("title") or "Unknown"),
                    homepage=e.get("url"),
                    description=res.description,
                    keywords=res.keywords or e.get("keywords", []),
                    signals=[CompetitorSignal(platform="web", title=e.get("title", ""), url=e.get("url"), snippet=e.get("snippet", ""))],
                    strength_score=res.strength_score,
                    positioning=res.positioning,
                )
            )
        except Exception as ex:
            logger.warning(f"[competitors] failed card draft for {e.get('url')}: {ex}")
    state["cards"] = cards
    logger.info(f"[competitors] ✅ drafted {len(cards)} cards")
    return state


def build_competitor_intel_graph():
    wf = StateGraph(CIState)
    wf.add_node("collect", collect_candidates)
    wf.add_node("enrich", enrich_candidates)
    wf.add_node("draft", draft_cards)
    wf.set_entry_point("collect")
    wf.add_edge("collect", "enrich")
    wf.add_edge("enrich", "draft")
    wf.add_edge("draft", END)
    return wf.compile()


competitor_intel_graph = build_competitor_intel_graph()


async def run_competitor_scan(req_dict: dict) -> dict:
    logger.info("--- Running Competitor Intelligence Agent ---")
    try:
        req = CompetitorScanRequest(**req_dict)
        init: CIState = {"req": req, "candidates": [], "enriched": [], "cards": [], "error": None}
        final = await competitor_intel_graph.ainvoke(init)
        if final.get("error"):
            return {"error": final["error"]}
        return CompetitorScanResponse(topic=req.query, competitors=final["cards"], notes="Synced from web signals.").model_dump()
    except Exception as e:
        logger.error(f"[competitors] critical error: {e}", exc_info=True)
        return {"error": "A critical error occurred while scanning competitors."}

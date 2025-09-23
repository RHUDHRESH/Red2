import asyncio
import logging
from typing import TypedDict, List, Dict

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_ollama.chat_models import ChatOllama
from agents.utils.toolkit import bind_llm_with_tools
from langgraph.graph import StateGraph, END

from services.registry import get_services
from schemas.research_schemas import ResearchRequest, ResearchResponse, ResearchFinding, SourceNote


logger = logging.getLogger(__name__)


class ResearchState(TypedDict):
    request: ResearchRequest
    sub_questions: List[str]
    search_results: List[Dict]
    pages: Dict[str, str]
    source_notes: List[SourceNote]
    findings: List[ResearchFinding]
    error: str | None


class SubQuestions(BaseModel):
    questions: List[str] = Field(description="3-5 specific sub-questions to guide research")


class PageNotes(BaseModel):
    title: str = ""
    key_points: List[str] = Field(default_factory=list)
    summary: str = ""


class Synthesis(BaseModel):
    findings: List[ResearchFinding]


def _llm_reasoning() -> ChatOllama:
    try:
        return get_services().llm_reasoning
    except Exception:
        # Fallback (base_url pulled from settings inside client)
        return ChatOllama(model="gemma3:4b", temperature=0.3)


async def plan_research(state: ResearchState) -> ResearchState:
    logger.info("[research] ▶ planning sub-questions …")
    tool = bind_llm_with_tools(_llm_reasoning(), ["web_search", "link_preview", "scrape_text", "extract_keywords"]).with_structured_output(SubQuestions)
    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are an elite web research strategist. Given a query, produce 3-5 crisp, non-overlapping sub-questions that, if answered, provide comprehensive coverage. Avoid trivial or redundant angles."),
        ("human", "Query: {query}")
    ])
    chain = prompt | tool
    try:
        result = await chain.ainvoke({"query": state['request'].query})
        questions = result.questions[:5]
        state['sub_questions'] = questions
        logger.info(f"[research] ✅ planned {len(questions)} sub-questions")
    except Exception as e:
        logger.warning(f"[research] planning failed: {e}; falling back to single query")
        state['sub_questions'] = [state['request'].query]
    return state


async def search_web(state: ResearchState) -> ResearchState:
    logger.info("[research] ▶ searching the web …")
    req = state['request']
    search = get_services().search
    seen = set()
    results: List[Dict] = []
    for q in state['sub_questions']:
        items = await search.search(q, max_results=req.max_results)
        for it in items:
            url = it.url
            if any(d for d in req.include_domains) and not any(d in url for d in req.include_domains):
                continue
            if any(d in url for d in req.exclude_domains):
                continue
            if url in seen:
                continue
            seen.add(url)
            results.append({"title": it.title, "url": url, "snippet": it.snippet, "q": q})
    state['search_results'] = results
    logger.info(f"[research] ✅ collected {len(results)} candidate results")
    return state


async def fetch_pages(state: ResearchState) -> ResearchState:
    logger.info("[research] ▶ fetching pages …")
    req = state['request']
    urls = [r["url"] for r in state['search_results']][: req.max_pages]
    pages = await get_services().scraper.scrape_many(urls, concurrency=6)
    state['pages'] = pages
    logger.info(f"[research] ✅ fetched {sum(1 for _, t in pages.items() if t)} pages")
    return state


async def note_pages(state: ResearchState) -> ResearchState:
    logger.info("[research] ▶ summarizing sources …")
    pages = state['pages']
    tool = _llm_reasoning().with_structured_output(PageNotes)
    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a precise analyst. Extract a compact title (if present), 3-7 key points (bullet ideas), and a concise summary from the provided page text. Avoid fluff."),
        ("human", "Page text (truncated):\n{page_text}")
    ])
    chain = prompt | tool
    sem = asyncio.Semaphore(3)
    source_notes: List[SourceNote] = []

    async def _one(url: str, text: str):
        if not text:
            return None
        snippet = text[:4000]  # keep LLM prompt manageable
        async with sem:
            try:
                res = await chain.ainvoke({"page_text": snippet})
                return SourceNote(url=url, title=res.title or "", key_points=res.key_points, summary=res.summary)
            except Exception as e:
                logger.warning(f"[research] summarization failed for {url}: {e}")
                return None

    tasks = [_one(u, t) for u, t in pages.items()]
    notes = await asyncio.gather(*tasks)
    source_notes = [n for n in notes if n is not None]
    state['source_notes'] = source_notes
    logger.info(f"[research] ✅ created notes for {len(source_notes)} sources")
    return state


async def synthesize(state: ResearchState) -> ResearchState:
    logger.info("[research] ▶ synthesizing findings …")
    tool = _llm_reasoning().with_structured_output(Synthesis)
    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a rigorous research synthesizer. Given notes from multiple sources, produce 5-10 concise findings with confidence estimates (0.0-1.0). Each finding should list 1-3 citation URLs backing it. Avoid duplication; ensure coverage and clarity."),
        ("human", "Query: {query}\n\nSource notes (JSON):\n{notes_json}")
    ])
    import json
    notes_json = json.dumps([n.model_dump() for n in state['source_notes']][:15])
    chain = prompt | tool
    try:
        res = await chain.ainvoke({"query": state['request'].query, "notes_json": notes_json})
        state['findings'] = res.findings
    except Exception as e:
        logger.error(f"[research] synthesis failed: {e}")
        state['error'] = "Synthesis failed"
    return state


def build_research_graph():
    wf = StateGraph(ResearchState)
    wf.add_node("plan", plan_research)
    wf.add_node("search", search_web)
    wf.add_node("fetch", fetch_pages)
    wf.add_node("note", note_pages)
    wf.add_node("synthesize", synthesize)
    wf.set_entry_point("plan")
    wf.add_edge("plan", "search")
    wf.add_edge("search", "fetch")
    wf.add_edge("fetch", "note")
    wf.add_edge("note", "synthesize")
    wf.add_edge("synthesize", END)
    return wf.compile()


research_graph = build_research_graph()


async def run_deep_research(req_dict: dict) -> dict:
    logger.info("--- Running Deep Research Agent ---")
    try:
        req = ResearchRequest(**req_dict)
        init: ResearchState = {
            "request": req,
            "sub_questions": [],
            "search_results": [],
            "pages": {},
            "source_notes": [],
            "findings": [],
            "error": None,
        }
        final = await research_graph.ainvoke(init)
        if final.get("error"):
            return {"error": final["error"]}
        return ResearchResponse(
            query=req.query,
            findings=final["findings"],
            sources=final["source_notes"],
        ).model_dump()
    except Exception as e:
        logger.error(f"[research] critical error: {e}", exc_info=True)
        return {"error": "A critical error occurred while performing research."}

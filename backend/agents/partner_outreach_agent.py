import re
import asyncio
import logging
from typing import TypedDict, List, Dict, Tuple

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_ollama.chat_models import ChatOllama
from langgraph.graph import StateGraph, END

from services.registry import get_services
from schemas.partner_schemas import (
    PartnerOutreachRequest,
    PartnerOutreachResponse,
    PartnerCandidate,
    EnrichedPartner,
    PartnerOutreachCard,
    OutreachTemplate,
)


logger = logging.getLogger(__name__)


class PartnerState(TypedDict):
    req: PartnerOutreachRequest
    candidates: List[PartnerCandidate]
    enriched: List[EnrichedPartner]
    cards: List[PartnerOutreachCard]
    error: str | None


class OutreachTool(BaseModel):
    subject: str
    email_body: str
    dm_message: str


def _llm() -> ChatOllama:
    try:
        return get_services().llm_reasoning
    except Exception:
        return ChatOllama(model="gemma3:4b", temperature=0.3)


def _extract_emails(text: str) -> List[str]:
    if not text:
        return []
    pat = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
    emails = pat.findall(text)
    # de-duplicate and filter obvious junk
    seen = set()
    out = []
    for e in emails:
        if e.lower() not in seen and len(e) <= 254:
            seen.add(e.lower())
            out.append(e)
    return out[:3]


async def find_partners(state: PartnerState) -> PartnerState:
    logger.info("[partners] ▶ finding nearby partners …")
    svc = get_services()
    req = state["req"]
    origin = (req.latitude, req.longitude)
    # Launch searches per type
    tasks = []
    for t in req.partner_types:
        tasks.append(svc.maps.nearby_search(origin, radius=req.radius_m, poi_type=t))
    groups = await asyncio.gather(*tasks)
    # Flatten and compute travel times
    pois = [p for g in groups for p in g][: max(20, req.max_partners)]
    pois = await svc.maps.get_travel_times(origin, pois)
    candidates: List[PartnerCandidate] = []
    for p in pois:
        candidates.append(
            PartnerCandidate(
                name=p.name,
                location=(p.location[0], p.location[1]),
                types=p.types,
                user_ratings_total=p.user_ratings_total,
                distance_m=p.distance_m,
                travel_time_min=p.travel_time_min,
            )
        )
    # Sort by distance and ratings; cap to max_partners
    candidates.sort(key=lambda c: (c.travel_time_min if c.travel_time_min else 9999, -c.user_ratings_total))
    state["candidates"] = candidates[: req.max_partners]
    logger.info(f"[partners] ✅ selected {len(state['candidates'])} candidates")
    return state


async def enrich_partners(state: PartnerState) -> PartnerState:
    logger.info("[partners] ▶ enriching partners …")
    svc = get_services()
    sem = asyncio.Semaphore(6)
    enriched: List[EnrichedPartner] = []

    async def _one(c: PartnerCandidate) -> EnrichedPartner:
        async with sem:
            q = f"{c.name} {state['req'].latitude:.4f},{state['req'].longitude:.4f}"
            hits = await svc.search.search(q, max_results=6)
            website = None
            linkedin = None
            for h in hits:
                url = h.url.lower()
                if not website and (url.startswith("http://") or url.startswith("https://")) and "linkedin.com" not in url:
                    website = h.url
                if not linkedin and "linkedin.com" in url:
                    linkedin = h.url
            text = ""
            email = None
            notes = ""
            if website:
                text = await svc.scraper.scrape_text(website)
                emails = _extract_emails(text)
                email = emails[0] if emails else None
                if text:
                    notes = await svc.summarizer.summarize(text[:3000], mode="brief")
            return EnrichedPartner(
                name=c.name,
                address=None,
                website=website,
                linkedin_url=linkedin,
                email=email,
                distance_m=c.distance_m,
                travel_time_min=c.travel_time_min,
                notes=notes,
            )

    enriched = await asyncio.gather(*[_one(c) for c in state["candidates"]])
    state["enriched"] = enriched
    logger.info(f"[partners] ✅ enriched {len(enriched)} partners")
    return state


async def draft_outreach(state: PartnerState) -> PartnerState:
    logger.info("[partners] ▶ drafting outreach copy …")
    tool = _llm().with_structured_output(OutreachTool)
    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a scrappy partnerships manager. Draft a short, polite, high-conversion outreach set for a local partnership:"
         " an email subject, a 5-7 sentence email body, and a 2-3 sentence DM message."
         " Make it specific to the partner context; include one concrete value proposition and a low-friction CTA."),
        ("human",
         "Business summary: {business}\nLanguage: {lang}\nPartner: {name}\nWebsite: {website}\nNotes: {notes}")
    ])
    chain = prompt | tool
    cards: List[PartnerOutreachCard] = []
    for p in state["enriched"]:
        try:
            res = await chain.ainvoke({
                "business": state["req"].business_summary,
                "lang": state["req"].language,
                "name": p.name,
                "website": p.website or "",
                "notes": p.notes or "",
            })
            cards.append(
                PartnerOutreachCard(
                    partner=p,
                    outreach=OutreachTemplate(subject=res.subject, email_body=res.email_body, dm_message=res.dm_message),
                )
            )
        except Exception as e:
            logger.warning(f"[partners] outreach draft failed for {p.name}: {e}")
    state["cards"] = cards
    logger.info(f"[partners] ✅ drafted outreach for {len(cards)} partners")
    return state


def build_partner_outreach_graph():
    wf = StateGraph(PartnerState)
    wf.add_node("find", find_partners)
    wf.add_node("enrich", enrich_partners)
    wf.add_node("outreach", draft_outreach)
    wf.set_entry_point("find")
    wf.add_edge("find", "enrich")
    wf.add_edge("enrich", "outreach")
    wf.add_edge("outreach", END)
    return wf.compile()


partner_outreach_graph = build_partner_outreach_graph()


async def run_partner_outreach(req_dict: dict) -> dict:
    logger.info("--- Running Partner Outreach Agent ---")
    try:
        req = PartnerOutreachRequest(**req_dict)
        init: PartnerState = {"req": req, "candidates": [], "enriched": [], "cards": [], "error": None}
        final = await partner_outreach_graph.ainvoke(init)
        if final.get("error"):
            return {"error": final["error"]}
        return PartnerOutreachResponse(area_center=(req.latitude, req.longitude), partners=final["cards"]).model_dump()
    except Exception as e:
        logger.error(f"[partners] critical error: {e}", exc_info=True)
        return {"error": "A critical error occurred while building the outreach list."}


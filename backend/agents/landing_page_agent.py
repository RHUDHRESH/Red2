import asyncio
import logging
from typing import TypedDict, List

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_ollama.chat_models import ChatOllama
from langgraph.graph import StateGraph, END

from services.registry import get_services
from schemas.landing_schemas import (
    LandingPageRequest,
    LandingPageResponse,
    LandingPageBlueprint,
    HeroSection,
    PageSection,
    FAQItem,
)


logger = logging.getLogger(__name__)


class LandingState(TypedDict):
    req: LandingPageRequest
    notes: str
    blueprint: LandingPageBlueprint | None
    error: str | None


class BlueprintTool(BaseModel):
    meta_title: str
    meta_description: str
    hero: HeroSection
    sections: List[PageSection] = Field(default_factory=list)
    social_proof: List[str] = Field(default_factory=list)
    faqs: List[FAQItem] = Field(default_factory=list)
    utm_campaign: str = ""


def _llm() -> ChatOllama:
    try:
        return get_services().llm_reasoning
    except Exception:
        return ChatOllama(model="gemma3:4b", temperature=0.3)


async def gather_reference_notes(state: LandingState) -> LandingState:
    logger.info("[landing] ▶ gathering reference notes …")
    svc = get_services()
    refs = state["req"].references
    if not refs:
        state["notes"] = ""
        return state
    sem = asyncio.Semaphore(5)
    chunks: List[str] = []

    async def _one(url: str):
        async with sem:
            try:
                text = await svc.scraper.scrape_text(url)
                if text:
                    summ = await svc.summarizer.summarize(text[:4000], mode="brief")
                    chunks.append(f"URL: {url}\n{summ}")
            except Exception:
                pass

    await asyncio.gather(*[_one(str(u)) for u in refs])
    state["notes"] = "\n\n".join(chunks)
    return state


async def draft_blueprint(state: LandingState) -> LandingState:
    logger.info("[landing] ▶ drafting blueprint …")
    tool = _llm().with_structured_output(BlueprintTool)
    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a skilled conversion copywriter. Create a compelling landing page blueprint using the provided inputs."
         " Keep it concise and conversion-oriented. Avoid claims that cannot be substantiated."),
        ("human",
         "Language: {lang}\nTone: {tone}\nTarget audience: {aud}\nProduct summary: {summary}\nValue props: {props}\nReference notes:\n{notes}")
    ])
    chain = prompt | tool
    req = state["req"]
    res = await chain.ainvoke({
        "lang": req.language,
        "tone": req.tone,
        "aud": req.target_audience or "",
        "summary": req.product_summary,
        "props": ", ".join(req.value_props) if req.value_props else "",
        "notes": state.get("notes", ""),
    })
    blueprint = LandingPageBlueprint(
        meta_title=res.meta_title,
        meta_description=res.meta_description,
        hero=res.hero,
        sections=res.sections,
        social_proof=res.social_proof,
        faqs=res.faqs,
        utm_campaign=res.utm_campaign,
        compliance_notes="",
    )
    state["blueprint"] = blueprint
    return state


async def moderate_blueprint(state: LandingState) -> LandingState:
    logger.info("[landing] ▶ moderating blueprint …")
    svc = get_services()
    bp = state["blueprint"]
    if bp is None:
        state["error"] = "No blueprint generated"
        return state
    # Concatenate text for moderation
    text = "\n".join([
        bp.hero.headline,
        bp.hero.subheadline,
        bp.meta_description,
        "\n".join([s.body for s in bp.sections]),
    ])
    report = await svc.moderation.evaluate(text)
    if not report.compliance_ok:
        bp.compliance_notes = f"Risk level: {report.risk_level}. Issues: {', '.join(report.risky_terms or [])}. Claims: {', '.join(report.legal_claims_detected or [])}. " + report.notes
    else:
        bp.compliance_notes = "Compliant (auto-assessed)."
    state["blueprint"] = bp
    return state


def build_landing_graph():
    wf = StateGraph(LandingState)
    wf.add_node("refs", gather_reference_notes)
    wf.add_node("draft", draft_blueprint)
    wf.add_node("moderate", moderate_blueprint)
    wf.set_entry_point("refs")
    wf.add_edge("refs", "draft")
    wf.add_edge("draft", "moderate")
    wf.add_edge("moderate", END)
    return wf.compile()


landing_graph = build_landing_graph()


async def run_landing_page(req_dict: dict) -> dict:
    logger.info("--- Running Landing Page Agent ---")
    try:
        req = LandingPageRequest(**req_dict)
        init: LandingState = {"req": req, "notes": "", "blueprint": None, "error": None}
        final = await landing_graph.ainvoke(init)
        if final.get("error"):
            return {"error": final["error"]}
        return LandingPageResponse(language=req.language, blueprint=final["blueprint"], used_references=req.references).model_dump()
    except Exception as e:
        logger.error(f"[landing] critical error: {e}", exc_info=True)
        return {"error": "A critical error occurred while generating the landing page blueprint."}


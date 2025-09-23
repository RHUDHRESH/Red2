import asyncio
import logging
from typing import TypedDict, List, Dict

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_ollama.chat_models import ChatOllama
from langgraph.graph import StateGraph, END

from services.registry import get_services
from schemas.evidence_schemas import (
    CopyAuditRequest,
    CopyAuditResponse,
    ClaimItem,
    ClaimEvidence,
    EvidenceItem,
    RewriteOption,
)


logger = logging.getLogger(__name__)


class EvidenceState(TypedDict):
    req: CopyAuditRequest
    claims: List[ClaimItem]
    claim_evidence: List[ClaimEvidence]
    notes: str
    error: str | None


class ClaimsTool(BaseModel):
    claims: List[ClaimItem] = Field(default_factory=list)


class Assessment(BaseModel):
    stance: str = Field(description="support|contradict|unclear")
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    reason: str = ""


def _llm_fast() -> ChatOllama:
    try:
        return get_services().llm_fast
    except Exception:
        return ChatOllama(model="gemma3:1b", temperature=0.0)


def _llm_reason() -> ChatOllama:
    try:
        return get_services().llm_reasoning
    except Exception:
        return ChatOllama(model="gemma3:4b", temperature=0.2)


async def extract_claims(state: EvidenceState) -> EvidenceState:
    logger.info("[evidence] ▶ extracting claims …")
    tool = _llm_fast().with_structured_output(ClaimsTool)
    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a careful fact-checker. Extract discrete factual or quantitative claims from the provided marketing copy."
         " Skip obvious puffery (e.g., 'tasty', 'awesome') unless paired with a measurable statement."
         " Classify severity as low|medium|high based on potential legal/brand risk if false."),
        ("human", "Copy:\n{copy}\n\nLanguage: {lang}")
    ])
    chain = prompt | tool
    res = await chain.ainvoke({"copy": state["req"].copy_text[:5000], "lang": state["req"].language})
    claims = res.claims[: state["req"].max_claims]
    state["claims"] = claims
    return state


async def gather_evidence(state: EvidenceState) -> EvidenceState:
    logger.info("[evidence] ▶ gathering sources …")
    svc = get_services()
    per = state["req"].evidence_per_claim
    sem = asyncio.Semaphore(6)

    async def _sources_for_claim(claim: ClaimItem) -> List[EvidenceItem]:
        q = claim.text
        web, news = await asyncio.gather(
            svc.search.search(q, max_results=per),
            (svc.news.search(q, max_results=per) if hasattr(svc, "news") else asyncio.sleep(0, result=[])),
        )
        wiki = []
        if hasattr(svc, "wikipedia"):
            try:
                wiki = await svc.wikipedia.search(q, limit=per)
            except Exception:
                wiki = []
        candidates: List[EvidenceItem] = []
        for h in web or []:
            candidates.append(EvidenceItem(url=h.url, title=h.title or "", summary=h.snippet or "", source_type="web"))
        for n in news or []:
            candidates.append(EvidenceItem(url=n.url, title=n.title or "", summary=n.snippet or "", source_type="news"))
        for w in wiki or []:
            if isinstance(w, dict):
                url = w.get("content_urls", {}).get("desktop", {}).get("page") or w.get("url") or ""
                title = w.get("title") or ""
                if url:
                    candidates.append(EvidenceItem(url=url, title=title, summary="", source_type="wiki"))
        # Enrich top few with preview/scrape
        async def _enrich(ev: EvidenceItem) -> EvidenceItem:
            async with sem:
                try:
                    preview = await svc.link_preview.fetch(str(ev.url))
                    text = await svc.scraper.scrape_text(str(ev.url))
                    summ = await svc.summarizer.summarize(text[:3000], mode="brief") if text else (preview.description or ev.summary)
                    ev.title = preview.title or ev.title
                    ev.summary = summ or ev.summary
                except Exception:
                    pass
                return ev

        enriched = await asyncio.gather(*[_enrich(ev) for ev in candidates[: per]])
        return [e for e in enriched if e.url]

    claim_evidence: List[ClaimEvidence] = []
    for claim in state["claims"]:
        evs = await _sources_for_claim(claim)
        claim_evidence.append(ClaimEvidence(claim=claim, evidence=evs))
    state["claim_evidence"] = claim_evidence
    return state


async def assess_support(state: EvidenceState) -> EvidenceState:
    logger.info("[evidence] ▶ assessing support …")
    llm = _llm_reason()
    tool = llm.with_structured_output(Assessment)
    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a meticulous verifier. Given a marketing claim and a source note, classify the stance as 'support', 'contradict', or 'unclear'."
         " Provide a confidence 0-1 and a one-sentence reason. Be conservative when evidence is weak."),
        ("human", "Claim: {claim}\nSource title: {title}\nSource summary:\n{summary}")
    ])
    chain = prompt | tool

    for ce in state["claim_evidence"]:
        assessed: List[EvidenceItem] = []
        for ev in ce.evidence:
            try:
                res = await chain.ainvoke({"claim": ce.claim.text, "title": ev.title, "summary": ev.summary})
                stance = res.stance.strip().lower()
                if stance not in ("support", "contradict", "unclear"):
                    stance = "unclear"
                ev.stance = stance  # type: ignore[assignment]
                ev.confidence = float(res.confidence)
            except Exception:
                ev.stance = "unclear"  # type: ignore[assignment]
                ev.confidence = 0.0
            assessed.append(ev)
        ce.evidence = assessed
    return state


class SuggestTool(BaseModel):
    options: List[str] = Field(default_factory=list, description="Multiple safer rewrite options with inline [n] citations")


async def suggest_rewrites(state: EvidenceState) -> EvidenceState:
    logger.info("[evidence] ▶ suggesting rewrites …")
    llm = _llm_reason()
    tool = llm.with_structured_output(SuggestTool)
    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a cautious marketer. Given a claim and a list of sources with short summaries, suggest safer rewrites."
         " Return 3-5 alternate phrasings that either qualify the claim or remove unverifiable parts."
         " Insert inline numeric citations like [1], [2] referencing the provided sources (in order)."),
        ("human", "Claim: {claim}\nSources (ordered):\n{sources}\nLanguage: {lang}")
    ])
    chain = prompt | tool
    for ce in state["claim_evidence"]:
        stances = [e.stance for e in ce.evidence]
        needs_rewrite = (not any(s == "support" for s in stances)) or any(s == "contradict" for s in stances)
        if not needs_rewrite:
            ce.suggestions = []
            continue
        lines = []
        for idx, ev in enumerate(ce.evidence[:5], start=1):
            lines.append(f"[{idx}] {ev.title} — {ev.summary}")
        try:
            res = await chain.ainvoke({
                "claim": ce.claim.text,
                "sources": "\n".join(lines) if lines else "(no strong sources)",
                "lang": state["req"].language,
            })
            ce.suggestions = [RewriteOption(text_with_citations=opt, rationale="Qualify or cite.") for opt in res.options[:5]]
        except Exception:
            ce.suggestions = []
    return state


def build_evidence_graph():
    wf = StateGraph(EvidenceState)
    wf.add_node("extract", extract_claims)
    wf.add_node("gather", gather_evidence)
    wf.add_node("assess", assess_support)
    wf.add_node("suggest", suggest_rewrites)
    wf.set_entry_point("extract")
    wf.add_edge("extract", "gather")
    wf.add_edge("gather", "assess")
    wf.add_edge("assess", "suggest")
    wf.add_edge("suggest", END)
    return wf.compile()


evidence_graph = build_evidence_graph()


async def run_copy_evidence_audit(req_dict: dict) -> dict:
    logger.info("--- Running Copy Evidence Audit Agent ---")
    try:
        req = CopyAuditRequest(**req_dict)
        init: EvidenceState = {"req": req, "claims": [], "claim_evidence": [], "notes": "", "error": None}
        final = await evidence_graph.ainvoke(init)
        if final.get("error"):
            return {"error": final["error"]}
        # summarize totals
        supported = 0
        contradictory = 0
        unsupported = 0
        for ce in final["claim_evidence"]:
            stances = [e.stance for e in ce.evidence]
            if any(s == "contradict" for s in stances):
                contradictory += 1
            elif any(s == "support" for s in stances):
                supported += 1
            else:
                unsupported += 1
        resp = CopyAuditResponse(
            total_claims=len(final["claims"]),
            supported_claims=supported,
            contradictory_claims=contradictory,
            unsupported_claims=unsupported,
            claims=final["claim_evidence"],
            notes="Classifications are best-effort. Review sources before publishing.",
        )
        return resp.model_dump()
    except Exception as e:
        logger.error(f"[evidence] critical error: {e}", exc_info=True)
        return {"error": "A critical error occurred while auditing copy."}

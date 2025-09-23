import asyncio
import logging
from typing import TypedDict, List

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_ollama.chat_models import ChatOllama
from langgraph.graph import StateGraph, END

from services.registry import get_services
from schemas.synthetic_schemas import (
    SyntheticGenRequest,
    SyntheticGenResponse,
    CohortSpec,
    CohortDataset,
    SyntheticPerson,
    SourceRef,
)


logger = logging.getLogger(__name__)


class SynthState(TypedDict):
    req: SyntheticGenRequest
    datasets: List[CohortDataset]
    notes: str
    error: str | None


class RulesTool(BaseModel):
    rules: List[str] = Field(default_factory=list, description="If-then style mapping rules for the cohort")


class SampleTool(BaseModel):
    people: List[SyntheticPerson] = Field(default_factory=list, description="Synthetic individuals")


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


async def pattern_mining_for(cohort: CohortSpec, lang: str) -> List[SourceRef]:
    svc = get_services()
    queries = [
        f"{cohort.name} consumer behavior India",
        f"{cohort.name} media consumption India",
        f"{cohort.name} shopping channel preference",
    ]
    sources: List[SourceRef] = []
    for q in queries:
        web = await svc.search.search(q, max_results=4)
        for h in web:
            try:
                preview = await svc.link_preview.fetch(h.url)
                text = await svc.scraper.scrape_text(h.url)
                summ = await svc.summarizer.summarize(text[:3000], mode="brief") if text else (preview.description or h.snippet)
                sources.append(SourceRef(url=h.url, title=preview.title or h.title, summary=summ or ""))
            except Exception:
                continue
        # Limit total sources
        if len(sources) >= 8:
            break
    return sources[:8]


async def build_rules(state: SynthState) -> SynthState:
    logger.info("[synth] ▶ building rules …")
    llm = _llm_reason()
    tool = llm.with_structured_output(RulesTool)
    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a behavioral data architect. Given a cohort spec and optional notes, produce if‑then rules linking traits to behaviors."
         " Use concise, machine-readable bullet rules: 'IF <trait pattern> THEN <behavior pattern> (freq=<low|med|high>)'."),
        ("human", "Cohort: {cohort_json}\nNotes:\n{notes}\nLanguage: {lang}")
    ])
    chain = prompt | tool
    datasets: List[CohortDataset] = []
    for c in state["req"].cohorts:
        notes = ""
        sources: List[SourceRef] = []
        if state["req"].include_pattern_mining:
            sources = await pattern_mining_for(c, state["req"].language)
            notes = "\n\n".join([s.summary for s in sources if s.summary])
        res = await chain.ainvoke({"cohort_json": c.model_dump_json(), "notes": notes, "lang": state["req"].language})
        datasets.append(CohortDataset(cohort=c.name, rules_used=res.rules, sources=sources, people=[]))
    state["datasets"] = datasets
    return state


async def sample_people(state: SynthState) -> SynthState:
    logger.info("[synth] ▶ generating samples …")
    llm = _llm_reason()
    tool = llm.with_structured_output(SampleTool)
    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a synthetic data generator. Using the cohort spec and rules, create realistic individuals."
         " Respect dependencies implied by rules and common sense for India. Vary media/shopping/offer response logically."),
        ("human", "Cohort: {cohort_json}\nRules:\n{rules}\nCount: {count}\nLanguage: {lang}")
    ])
    chain = prompt | tool

    out: List[CohortDataset] = []
    for c, ds in zip(state["req"].cohorts, state["datasets"]):
        count = c.target_size
        batch = 50
        people: List[SyntheticPerson] = []
        for start in range(0, count, batch):
            n = min(batch, count - start)
            res = await chain.ainvoke({
                "cohort_json": c.model_dump_json(),
                "rules": "\n".join(ds.rules_used),
                "count": n,
                "lang": state["req"].language,
            })
            # Ensure cohort name and basic normalization
            for p in res.people:
                p.cohort = c.name
            people.extend(res.people)
        ds.people = people
        out.append(ds)
    state["datasets"] = out
    return state


async def validate_dataset(state: SynthState) -> SynthState:
    logger.info("[synth] ▶ validating dataset …")
    # Lightweight validation: ensure non-empty basic fields and rule coverage mention
    for ds in state["datasets"]:
        # No-op placeholder for extensible human-in-the-loop
        if not ds.rules_used:
            ds.rules_used = ["IF (unknown) THEN (baseline behaviors) (freq=low)"]
    return state


async def sdv_augment(state: SynthState) -> SynthState:
    logger.info("[synth] ▶ SDV augment (optional) …")
    if not state["req"].use_sdv:
        return state
    try:
        import pandas as pd  # type: ignore
        from sdv.tabular import GaussianCopula  # type: ignore
    except Exception:
        logger.warning("SDV not available; skipping augmentation")
        return state
    for ds in state["datasets"]:
        try:
            if not ds.people:
                continue
            df = pd.DataFrame([p.model_dump() if hasattr(p, 'model_dump') else p for p in ds.people])
            model = GaussianCopula()
            model.fit(df)
            extra = model.sample(min(100, max(0,  ds.people.__len__() // 2)))
            for _, row in extra.iterrows():
                try:
                    ds.people.append(SyntheticPerson(**row.to_dict()))
                except Exception:
                    continue
        except Exception:
            continue
    return state


async def survey_synthesis(state: SynthState) -> SynthState:
    logger.info("[synth] ▶ survey synthesis …")
    import base64
    llm = _llm_fast()
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Create a CSV with columns: channel, offer, purchase_freq, trust_source. 50 rows, realistic for the cohort."),
        ("human", "Cohort name: {name}\nLanguage: {lang}")
    ])
    chain = prompt | llm
    for ds in state["datasets"]:
        try:
            csv_text = (await chain.ainvoke({"name": ds.cohort, "lang": state["req"].language})).content
            ds.survey_csv_base64 = base64.b64encode(csv_text.encode("utf-8")).decode("ascii") if csv_text else None
        except Exception:
            ds.survey_csv_base64 = None
    return state


def build_synthetic_graph():
    wf = StateGraph(SynthState)
    wf.add_node("rules", build_rules)
    wf.add_node("sample", sample_people)
    wf.add_node("sdv", sdv_augment)
    wf.add_node("validate", validate_dataset)
    wf.add_node("survey", survey_synthesis)
    wf.set_entry_point("rules")
    wf.add_edge("rules", "sample")
    wf.add_edge("sample", "sdv")
    wf.add_edge("sdv", "validate")
    wf.add_edge("validate", "survey")
    wf.add_edge("survey", END)
    return wf.compile()


synthetic_graph = build_synthetic_graph()


async def run_synthetic_generation(req_dict: dict) -> dict:
    logger.info("--- Running Synthetic Behavioral Data Agent ---")
    try:
        req = SyntheticGenRequest(**req_dict)
        init: SynthState = {"req": req, "datasets": [], "notes": "", "error": None}
        final = await synthetic_graph.ainvoke(init)
        if final.get("error"):
            return {"error": final["error"]}
        return SyntheticGenResponse(cohorts=final["datasets"], notes="Synthetic ≠ random; review rules and iterate.").model_dump()
    except Exception as e:
        logger.error(f"[synth] critical error: {e}", exc_info=True)
        return {"error": "A critical error occurred while generating synthetic behavioral data."}

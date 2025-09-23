import logging
from typing import TypedDict

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_ollama.chat_models import ChatOllama
from langgraph.graph import StateGraph, END

from services.registry import get_services
from schemas.asset_schemas import CaseStudyOutlineRequest, CaseStudyOutlineResponse, CaseStudySection


logger = logging.getLogger(__name__)


class CSState(TypedDict):
    req: CaseStudyOutlineRequest
    resp: CaseStudyOutlineResponse | None
    error: str | None


class CSTool(BaseModel):
    title: str
    sections: list[CaseStudySection] = Field(default_factory=list)


def _llm() -> ChatOllama:
    try:
        return get_services().llm_reasoning
    except Exception:
        return ChatOllama(model="gemma3:4b", temperature=0.3)


async def draft_case_study(state: CSState) -> CSState:
    logger.info("[case-study] ▶ drafting outline …")
    tool = _llm().with_structured_output(CSTool)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Draft a concise case study outline with sections (Challenge, Solution, Results, Proof), each with 3-5 bullets."),
        ("human", "Client: {client}\nChallenge: {challenge}\nSolution: {solution}\nResults: {results}\nLanguage: {lang}")
    ])
    chain = prompt | tool
    req = state["req"]
    res = await chain.ainvoke({
        "client": req.client,
        "challenge": req.challenge,
        "solution": req.solution,
        "results": req.results,
        "lang": req.language,
    })
    state["resp"] = CaseStudyOutlineResponse(title=res.title, sections=res.sections)
    return state


def build_case_study_graph():
    wf = StateGraph(CSState)
    wf.add_node("draft", draft_case_study)
    wf.set_entry_point("draft")
    wf.add_edge("draft", END)
    return wf.compile()


case_study_graph = build_case_study_graph()


async def run_case_study_outline(req_dict: dict) -> dict:
    logger.info("--- Running Case Study Outline Agent ---")
    try:
        req = CaseStudyOutlineRequest(**req_dict)
        init: CSState = {"req": req, "resp": None, "error": None}
        final = await case_study_graph.ainvoke(init)
        if final.get("error"):
            return {"error": final["error"]}
        return final["resp"].model_dump()
    except Exception as e:
        logger.error(f"[case-study] critical error: {e}", exc_info=True)
        return {"error": "A critical error occurred while generating the case study outline."}


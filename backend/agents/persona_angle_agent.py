import logging
from typing import TypedDict, List

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_ollama.chat_models import ChatOllama
from langgraph.graph import StateGraph, END

from services.registry import get_services
from schemas.asset_schemas import PersonaAngleRequest, PersonaAngleResponse, PersonaAngleItem


logger = logging.getLogger(__name__)


class PAState(TypedDict):
    req: PersonaAngleRequest
    resp: PersonaAngleResponse | None
    error: str | None


class PATool(BaseModel):
    items: List[PersonaAngleItem] = Field(default_factory=list)


def _llm() -> ChatOllama:
    try:
        return get_services().llm_reasoning
    except Exception:
        return ChatOllama(model="gemma3:4b", temperature=0.4)


async def draft_angles(state: PAState) -> PAState:
    logger.info("[angles] ▶ drafting persona angles …")
    tool = _llm().with_structured_output(PATool)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "For each persona, propose a distinct content angle and 2-3 example lines that would resonate."),
        ("human", "Topic: {topic}\nPersonas: {personas}\nTone: {tone}\nLanguage: {lang}")
    ])
    chain = prompt | tool
    req = state["req"]
    res = await chain.ainvoke({"topic": req.topic, "personas": ", ".join(req.personas), "tone": req.tone, "lang": req.language})
    state["resp"] = PersonaAngleResponse(items=res.items)
    return state


def build_persona_angle_graph():
    wf = StateGraph(PAState)
    wf.add_node("draft", draft_angles)
    wf.set_entry_point("draft")
    wf.add_edge("draft", END)
    return wf.compile()


persona_angle_graph = build_persona_angle_graph()


async def run_persona_angle(req_dict: dict) -> dict:
    logger.info("--- Running Persona Angle Agent ---")
    try:
        req = PersonaAngleRequest(**req_dict)
        init: PAState = {"req": req, "resp": None, "error": None}
        final = await persona_angle_graph.ainvoke(init)
        if final.get("error"):
            return {"error": final["error"]}
        return final["resp"].model_dump()
    except Exception as e:
        logger.error(f"[angles] critical error: {e}", exc_info=True)
        return {"error": "A critical error occurred while generating persona angles."}


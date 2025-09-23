import logging
from typing import TypedDict

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_ollama.chat_models import ChatOllama
from langgraph.graph import StateGraph, END

from services.registry import get_services
from schemas.asset_schemas import DripCampaignRequest, DripCampaignResponse, DripEmail


logger = logging.getLogger(__name__)


class DCState(TypedDict):
    req: DripCampaignRequest
    resp: DripCampaignResponse | None
    error: str | None


class DCTool(BaseModel):
    emails: list[DripEmail] = Field(default_factory=list)


def _llm() -> ChatOllama:
    try:
        return get_services().llm_reasoning
    except Exception:
        return ChatOllama(model="gemma3:4b", temperature=0.3)


async def draft_drip(state: DCState) -> DCState:
    logger.info("[drip] ▶ drafting email sequence …")
    tool = _llm().with_structured_output(DCTool)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Design a drip sequence with day offsets, focused subjects, and 3-5 bullet outlines per email."),
        ("human", "Goal: {goal}\nEmails: {n}\nCadence days: {cad}\nTone: {tone}\nLanguage: {lang}")
    ])
    chain = prompt | tool
    req = state["req"]
    res = await chain.ainvoke({"goal": req.goal, "n": req.emails_count, "cad": req.cadence_days, "tone": req.tone, "lang": req.language})
    state["resp"] = DripCampaignResponse(emails=res.emails[: req.emails_count])
    return state


def build_drip_graph():
    wf = StateGraph(DCState)
    wf.add_node("draft", draft_drip)
    wf.set_entry_point("draft")
    wf.add_edge("draft", END)
    return wf.compile()


drip_graph = build_drip_graph()


async def run_drip_campaign(req_dict: dict) -> dict:
    logger.info("--- Running Drip Campaign Agent ---")
    try:
        req = DripCampaignRequest(**req_dict)
        init: DCState = {"req": req, "resp": None, "error": None}
        final = await drip_graph.ainvoke(init)
        if final.get("error"):
            return {"error": final["error"]}
        return final["resp"].model_dump()
    except Exception as e:
        logger.error(f"[drip] critical error: {e}", exc_info=True)
        return {"error": "A critical error occurred while generating the drip campaign."}


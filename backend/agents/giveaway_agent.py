import logging
from typing import TypedDict, List

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_ollama.chat_models import ChatOllama
from langgraph.graph import StateGraph, END

from services.registry import get_services
from schemas.asset_schemas import GiveawayRequest, GiveawayResponse


logger = logging.getLogger(__name__)


class GAState(TypedDict):
    req: GiveawayRequest
    resp: GiveawayResponse | None
    error: str | None


class GATool(BaseModel):
    announcement: str
    rules: List[str] = Field(default_factory=list)
    steps: List[str] = Field(default_factory=list)
    hashtags: List[str] = Field(default_factory=list)


def _llm() -> ChatOllama:
    try:
        return get_services().llm_reasoning
    except Exception:
        return ChatOllama(model="gemma3:4b", temperature=0.3)


async def draft_giveaway(state: GAState) -> GAState:
    logger.info("[giveaway] ▶ drafting giveaway …")
    tool = _llm().with_structured_output(GATool)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Plan a simple platform-compliant giveaway with clear rules and steps, and a catchy announcement copy."),
        ("human", "Goal: {goal}\nPrize: {prize}\nPlatform: {platform}\nTone: {tone}\nLanguage: {lang}")
    ])
    chain = prompt | tool
    req = state["req"]
    res = await chain.ainvoke({"goal": req.goal, "prize": req.prize, "platform": req.platform, "tone": req.tone, "lang": req.language})
    tags = [h if h.startswith("#") else f"#{h}" for h in res.hashtags][:12]
    state["resp"] = GiveawayResponse(announcement=res.announcement, rules=res.rules, steps=res.steps, hashtags=tags)
    return state


def build_giveaway_graph():
    wf = StateGraph(GAState)
    wf.add_node("draft", draft_giveaway)
    wf.set_entry_point("draft")
    wf.add_edge("draft", END)
    return wf.compile()


giveaway_graph = build_giveaway_graph()


async def run_giveaway(req_dict: dict) -> dict:
    logger.info("--- Running Giveaway Agent ---")
    try:
        req = GiveawayRequest(**req_dict)
        init: GAState = {"req": req, "resp": None, "error": None}
        final = await giveaway_graph.ainvoke(init)
        if final.get("error"):
            return {"error": final["error"]}
        return final["resp"].model_dump()
    except Exception as e:
        logger.error(f"[giveaway] critical error: {e}", exc_info=True)
        return {"error": "A critical error occurred while generating the giveaway plan."}

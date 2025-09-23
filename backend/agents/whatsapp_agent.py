import logging
from typing import TypedDict

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_ollama.chat_models import ChatOllama
from langgraph.graph import StateGraph, END

from services.registry import get_services
from schemas.asset_schemas import WhatsAppRequest, WhatsAppResponse


logger = logging.getLogger(__name__)


class WAState(TypedDict):
    req: WhatsAppRequest
    resp: WhatsAppResponse | None
    error: str | None


class WATool(BaseModel):
    messages: list[str] = Field(default_factory=list)


def _llm() -> ChatOllama:
    try:
        return get_services().llm_fast
    except Exception:
        return ChatOllama(model="gemma3:1b", temperature=0.0)


async def draft_whatsapp(state: WAState) -> WAState:
    logger.info("[whatsapp] ▶ drafting broadcast messages …")
    tool = _llm().with_structured_output(WATool)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Generate WhatsApp-friendly messages (1-2 lines), natural, with soft CTA. Avoid spammy formatting."),
        ("human", "Goal: {goal}\nOffer: {offer}\nTone: {tone}\nLanguage: {lang}\nCount: {count}")
    ])
    chain = prompt | tool
    req = state["req"]
    res = await chain.ainvoke({"goal": req.campaign_goal, "offer": req.offer, "tone": req.tone, "lang": req.language, "count": req.count})
    state["resp"] = WhatsAppResponse(messages=res.messages[: req.count])
    return state


def build_whatsapp_graph():
    wf = StateGraph(WAState)
    wf.add_node("draft", draft_whatsapp)
    wf.set_entry_point("draft")
    wf.add_edge("draft", END)
    return wf.compile()


whatsapp_graph = build_whatsapp_graph()


async def run_whatsapp(req_dict: dict) -> dict:
    logger.info("--- Running WhatsApp Agent ---")
    try:
        req = WhatsAppRequest(**req_dict)
        init: WAState = {"req": req, "resp": None, "error": None}
        final = await whatsapp_graph.ainvoke(init)
        if final.get("error"):
            return {"error": final["error"]}
        return final["resp"].model_dump()
    except Exception as e:
        logger.error(f"[whatsapp] critical error: {e}", exc_info=True)
        return {"error": "A critical error occurred while generating WhatsApp messages."}


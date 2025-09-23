import logging
from typing import TypedDict

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel
from langchain_ollama.chat_models import ChatOllama
from langgraph.graph import StateGraph, END

from services.registry import get_services
from schemas.asset_schemas import EmailRequest, EmailResponse
from .utils.postprocess import clamp_length
from .utils.policies import EMAIL


logger = logging.getLogger(__name__)


class EMState(TypedDict):
    req: EmailRequest
    resp: EmailResponse | None
    error: str | None


class EMTool(BaseModel):
    subject: str
    preheader: str
    body_html: str


def _llm() -> ChatOllama:
    try:
        return get_services().llm_reasoning
    except Exception:
        return ChatOllama(model="gemma3:4b", temperature=0.2)


async def draft_email(state: EMState) -> EMState:
    logger.info("[email] ▶ drafting email …")
    tool = _llm().with_structured_output(EMTool)
    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a lifecycle marketer. Draft a high-conversion email (subject, preheader, HTML body) for the audience. Keep body skimmable with short paragraphs and bold CTAs."),
        ("human",
         "Product: {summary}\nAudience: {aud}\nOffer: {offer}\nTone: {tone}\nLanguage: {lang}")
    ])
    chain = prompt | tool
    req = state["req"]
    res = await chain.ainvoke({"summary": req.product_summary, "aud": req.audience, "offer": req.offer, "tone": req.tone, "lang": req.language})
    subj = clamp_length(res.subject, EMAIL["subject_max"]) if res.subject else ""
    pre = clamp_length(res.preheader, EMAIL["preheader_max"]) if res.preheader else ""
    state["resp"] = EmailResponse(subject=subj, preheader=pre, body_html=res.body_html)
    return state


def build_email_graph():
    wf = StateGraph(EMState)
    wf.add_node("draft", draft_email)
    wf.set_entry_point("draft")
    wf.add_edge("draft", END)
    return wf.compile()


email_graph = build_email_graph()


async def run_email(req_dict: dict) -> dict:
    logger.info("--- Running Email Agent ---")
    try:
        req = EmailRequest(**req_dict)
        init: EMState = {"req": req, "resp": None, "error": None}
        final = await email_graph.ainvoke(init)
        if final.get("error"):
            return {"error": final["error"]}
        return final["resp"].model_dump()
    except Exception as e:
        logger.error(f"[email] critical error: {e}", exc_info=True)
        return {"error": "A critical error occurred while generating the email."}

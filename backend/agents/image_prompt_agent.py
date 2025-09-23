import logging
from typing import TypedDict

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel
from langchain_ollama.chat_models import ChatOllama
from langgraph.graph import StateGraph, END

from services.registry import get_services
from schemas.asset_schemas import ImagePromptRequest, ImagePromptResponse


logger = logging.getLogger(__name__)


class IPState(TypedDict):
    req: ImagePromptRequest
    resp: ImagePromptResponse | None
    error: str | None


class IPTool(BaseModel):
    stable_diffusion_prompt: str
    dalle_prompt: str
    negative_prompt: str = ""
    composition_notes: str = ""


def _llm() -> ChatOllama:
    try:
        return get_services().llm_reasoning
    except Exception:
        return ChatOllama(model="gemma3:4b", temperature=0.3)


async def draft_image_prompt(state: IPState) -> IPState:
    logger.info("[image] ▶ drafting image prompts …")
    tool = _llm().with_structured_output(IPTool)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Create detailed image generation prompts (Stable Diffusion + DALL·E) and a negative prompt. Include palette if provided."),
        ("human", "Concept: {concept}\nStyle: {style}\nPalette: {palette}\nLanguage: {lang}")
    ])
    chain = prompt | tool
    req = state["req"]
    palette = ", ".join(req.brand_palette) if req.brand_palette else ""
    res = await chain.ainvoke({"concept": req.concept, "style": req.style, "palette": palette, "lang": req.language})
    state["resp"] = ImagePromptResponse(stable_diffusion_prompt=res.stable_diffusion_prompt, dalle_prompt=res.dalle_prompt, negative_prompt=res.negative_prompt, composition_notes=res.composition_notes)
    return state


def build_image_prompt_graph():
    wf = StateGraph(IPState)
    wf.add_node("draft", draft_image_prompt)
    wf.set_entry_point("draft")
    wf.add_edge("draft", END)
    return wf.compile()


image_prompt_graph = build_image_prompt_graph()


async def run_image_prompt(req_dict: dict) -> dict:
    logger.info("--- Running Image Prompt Agent ---")
    try:
        req = ImagePromptRequest(**req_dict)
        init: IPState = {"req": req, "resp": None, "error": None}
        final = await image_prompt_graph.ainvoke(init)
        if final.get("error"):
            return {"error": final["error"]}
        return final["resp"].model_dump()
    except Exception as e:
        logger.error(f"[image] critical error: {e}", exc_info=True)
        return {"error": "A critical error occurred while generating image prompts."}


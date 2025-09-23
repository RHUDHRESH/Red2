import logging
import json
import asyncio
import time
from typing import TypedDict, List

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_ollama.chat_models import ChatOllama
from agents.utils.toolkit import bind_llm_with_tools
from langgraph.graph import StateGraph, END

from core.config import settings
from services.registry import get_services
from schemas.positioning_schemas import PositioningOptionCard

# --- Configuration & Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Models ---
# Use the reasoning model for all tasks here, as positioning is a high-level strategic task.
def _get_reasoning_llm() -> ChatOllama:
    try:
        return get_services().llm_reasoning
    except Exception:
        # Fallback if services not initialized (e.g., in isolated scripts)
        return ChatOllama(model=settings.OLLAMA_REASONING_MODEL, temperature=0.4, base_url=settings.OLLAMA_BASE_URL)

# --- Agent State ---
class PositioningAgentState(TypedDict):
    """
    Defines the state for the positioning options generation graph.
    """
    # In a real app, this would be richer context from the intake interview
    # For now, we'll use a placeholder representing gathered facts.
    intake_summary: str
    generated_options: List[PositioningOptionCard] | None
    validated_options: List[PositioningOptionCard] | None
    final_options: List[PositioningOptionCard] | None
    error: str | None

# --- Pydantic Models for Structured LLM Outputs (Tools) ---
class GeneratedOptionsTool(BaseModel):
    """A tool for the LLM to output a list of three distinct positioning option cards."""
    options: List[PositioningOptionCard] = Field(
        description="A list of exactly three distinct, high-quality positioning option cards."
    )

class ValidationScore(BaseModel):
    """A tool for the self-critique node to score a single positioning card."""
    is_valid: bool = Field(description="Whether the card meets all the criteria (True/False).")
    score: int = Field(description="A score from 1-10 based on the card's overall strategic strength.")
    reasoning: str = Field(description="A brief justification for the score and validity assessment.")

# --- Agent Nodes ---
async def generate_positioning_options(state: PositioningAgentState) -> PositioningAgentState:
    """
    Node 1: The creative core. Takes the intake summary and generates three
    initial positioning options.
    """
    logger.info("[positioning] ▶ generating initial options …")
    try:
        t0 = time.perf_counter()
        generator_tool = bind_llm_with_tools(_get_reasoning_llm(), ["extract_keywords", "summarize_text"]).with_structured_output(GeneratedOptionsTool)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system",
             "You are a world-class category designer and brand strategist, mentored by Al Ries and April Dunford. "
             "Your task is to take a summary of a founder's business and generate THREE distinct, compelling positioning options. "
             "Each option must be a complete 'PositioningOptionCard' and include:\n"
             "- **one_word**: A single, powerful word to own (e.g., 'Speed', 'Authentic').\n"
             "- **category**: A new category of their own (e.g., 'Late-Night Study Fuel', '10-Minute Professional Lunch').\n"
             "- **tagline**: A short, memorable tagline (under 10 words).\n"
             "- **pillars**: Three value pillars with proof points (use placeholders like '[Metric]' if needed).\n"
             "- **behavior_lever**: A psychological lever like 'Scarcity' or 'Convenience'.\n"
             "- **first_assets**: Three concrete, low-cost marketing assets for the first 72 hours.\n"
             "- **risks**: Two potential risks and how to mitigate them.\n"
             "Use the 'GeneratedOptionsTool' to format your entire response."),
            ("human",
             "Here is the summary of the founder's business based on our intake interview:\n\n"
             "'{intake_summary}'\n\n"
             "Please generate three distinct positioning options.")
        ])
        
        chain = prompt | generator_tool
        result = await chain.ainvoke({"intake_summary": state['intake_summary']})
        
        state['generated_options'] = result.options
        dt = time.perf_counter() - t0
        logger.info(f"[positioning] ✅ generated {len(result.options)} options in {dt:.2f}s")
        return state
    except Exception as e:
        logger.error(f"[positioning] ✖ error generating options: {e}", exc_info=True)
        state['error'] = "The AI failed to generate initial positioning options."
        return state

async def validate_and_score_options(state: PositioningAgentState) -> PositioningAgentState:
    """
    Node 2: The self-critique loop. The agent reviews its own work, scoring each
    option for strategic soundness and adherence to the rules.
    """
    logger.info("[positioning] ▶ validating and scoring options …")
    if state.get('error'):
        return state
    
    try:
        t0 = time.perf_counter()
        validator_tool = bind_llm_with_tools(_get_reasoning_llm(), ["extract_keywords"]).with_structured_output(ValidationScore)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system",
             "You are a skeptical and pragmatic marketing director. Your job is to critique a positioning card generated by a creative strategist. "
             "Score the card from 1-10 on its strategic strength. Is it distinctive? Believable? Defensible? Does it have a clear point of view? "
             "A score of 8+ is considered valid. Use the 'ValidationScore' tool for your response."),
            ("human", "Please validate and score this positioning card:\n\n```json\n{option_json}\n```")
        ])
        
        chain = prompt | validator_tool

        # Validate concurrently with a small cap (3) to reduce wall time
        sem = asyncio.Semaphore(3)
        validated: List[PositioningOptionCard] = []

        async def _validate(opt: PositioningOptionCard):
            async with sem:
                res = await chain.ainvoke({"option_json": opt.model_dump_json()})
                if res.is_valid and res.score >= 8:
                    opt.score = res.score
                    logger.info(
                        f"[positioning] ✔ validated '{opt.one_word}' score={res.score} — {res.reasoning}"
                    )
                    return opt
                else:
                    logger.warning(
                        f"[positioning] ✖ rejected '{opt.one_word}' score={res.score} — {res.reasoning}"
                    )
                    return None

        results = await asyncio.gather(*(_validate(o) for o in state['generated_options']))
        validated = [o for o in results if o is not None]

        if not validated:
            raise ValueError("No options passed the validation and scoring process.")
            
        state['validated_options'] = validated
        dt = time.perf_counter() - t0
        logger.info(f"[positioning] ✅ validated {len(validated)}/{len(state['generated_options'])} options in {dt:.2f}s")
        return state
    except Exception as e:
        logger.error(f"[positioning] ✖ error during validation: {e}", exc_info=True)
        state['error'] = "The AI failed to validate its own strategic options."
        return state

async def sort_and_finalize(state: PositioningAgentState) -> PositioningAgentState:
    """
    Node 3: The final step. Sorts the validated options by score to present
    the best ones first.
    """
    logger.info("[positioning] ▶ sorting and finalizing …")
    if state.get('error'):
        return state
    
    validated_options = state['validated_options']
    # Sort the list of options in descending order based on their score
    sorted_options = sorted(validated_options, key=lambda x: x.score, reverse=True)
    
    state['final_options'] = sorted_options
    logger.info(f"[positioning] ✅ finalized {len(sorted_options)} options")
    return state

# --- Graph Definition ---
def build_positioning_agent_graph():
    workflow = StateGraph(PositioningAgentState)
    workflow.add_node("generate_options", generate_positioning_options)
    workflow.add_node("validate_and_score", validate_and_score_options)
    workflow.add_node("sort_and_finalize", sort_and_finalize)
    
    workflow.set_entry_point("generate_options")
    workflow.add_edge("generate_options", "validate_and_score")
    workflow.add_edge("validate_and_score", "sort_and_finalize")
    workflow.add_edge("sort_and_finalize", END)
    
    return workflow.compile()

positioning_agent_graph = build_positioning_agent_graph()

# --- Main Agent Runner Function ---
async def run_positioning_agent(intake_context: dict) -> dict:
    """
    Entrypoint to run the positioning agent.
    """
    logger.info("--- Running Positioning Options Agent ---")
    try:
        # Build a simple summary from the provided intake context (facts/claims/taboos)
        facts = intake_context.get("facts") or []
        claims = intake_context.get("claims") or []
        taboos = intake_context.get("taboos") or []
        if facts or claims:
            intake_summary = (
                "Facts: " + "; ".join(facts) + ". " if facts else ""
            ) + (
                "Claims: " + "; ".join(claims) + ". " if claims else ""
            ) + (
                "Taboos: " + "; ".join(taboos) + "." if taboos else ""
            )
        else:
            # Fallback placeholder when no context is provided
            intake_summary = (
                "A founder is starting a local food business and needs distinct, "
                "defensible positioning options tailored to their audience."
            )

        initial_state = {"intake_summary": intake_summary}
        
        final_state = await positioning_agent_graph.ainvoke(initial_state)

        if final_state.get('error'):
            logger.error(f"  > Agent finished with error: {final_state['error']}")
            return {"error": final_state['error']}
        
        logger.info("  > Agent finished successfully.")
        return {"options": [opt.model_dump() for opt in final_state['final_options']]}

    except Exception as e:
        logger.error(f"  > Critical error running positioning agent: {e}", exc_info=True)
        return {"error": "A critical error occurred while setting up the positioning agent."}

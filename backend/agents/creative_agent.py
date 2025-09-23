import uuid
import logging
from typing import TypedDict, List
import asyncio

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_ollama.chat_models import ChatOllama
from langgraph.graph import StateGraph, END

from core.config import settings
from services.registry import get_services
from schemas.move_schemas import StrikePlan, AssetBrief
from schemas.creative_schemas import CreativeAsset, AssetPackage
from schemas.outcome_schemas import OutcomeCharter

# --- Configuration & Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Models ---
# Creative generation requires the most capable model.
def _get_reasoning_llm() -> ChatOllama:
    try:
        return get_services().llm_reasoning
    except Exception:
        return ChatOllama(model=settings.OLLAMA_REASONING_MODEL, temperature=0.6, base_url=settings.OLLAMA_BASE_URL)

# --- Agent State ---
class CreativeAgentState(TypedDict):
    """
    Defines the state for the creative generation graph.
    It takes a strike plan and produces a package of completed creative assets.
    """
    strike_plan: StrikePlan
    outcome_charter: OutcomeCharter
    asset_package: AssetPackage | None
    error: str | None

# --- Pydantic Models for Structured LLM Outputs (Tools) ---
class GeneratedAsset(BaseModel):
    """A tool for the LLM to output a single, fully-realized creative asset."""
    headline: str | None = Field(default=None, description="The primary headline or hook for the ad/post. Should be punchy and attention-grabbing.")
    body_copy: str = Field(..., description="The main text content of the asset. This should be persuasive and aligned with the brief's key message.")
    visual_suggestion: str = Field(..., description="A concrete and vivid suggestion for the visual element, e.g., 'A top-down, fast-motion video showing a delicious-looking biryani being packed into a spill-proof container.'")

# --- Agent Node ---
async def generate_single_asset(brief: AssetBrief, charter: OutcomeCharter) -> CreativeAsset | None:
    """
    An async helper function to process a single asset brief. This allows us to generate
    multiple creatives in parallel, speeding up the process significantly.
    """
    logger.info(f"--- Generating Creative for Brief: {brief.id} ({brief.key_message}) ---")
    try:
        asset_generator_tool = _get_reasoning_llm().with_structured_output(GeneratedAsset)

        prompt = ChatPromptTemplate.from_messages([
            ("system",
             "You are a Senior Creative Director at a top advertising agency in India. You are an expert in crafting compelling, channel-native content for direct-to-consumer brands. "
             "Your task is to take a creative brief and generate the actual creative content (headline, body, visual idea).\n\n"
             "Key principles:\n"
             "- **Hook is everything**: The headline must grab attention in under 3 seconds.\n"
             "- **Be direct and clear**: The body copy must clearly communicate the value proposition and the call to action.\n"
             "- **Visuals sell**: The visual suggestion should be vivid, specific, and achievable for a small business.\n"
             "- **Channel Native**: Tailor the tone and format to the specified channel (e.g., Instagram Reels should be fast-paced and visual; LinkedIn posts should be more professional).\n\n"
             "Use the 'GeneratedAsset' tool to format your entire response."),
            ("human",
             "Please generate the creative asset based on the following brief:\n\n"
             "**Overall Campaign Objective**: {objective}\n"
             "**Target Metric**: {metric}\n\n"
             "**Creative Brief Details**:\n"
             "- **Asset ID**: {asset_id}\n"
             "- **Channel**: {channel}\n"
             "- **Asset Type**: {asset_type}\n"
             "- **Key Message**: {key_message}\n"
             "- **Call to Action**: {cta}\n\n"
             "Now, generate the creative content.")
        ])

        chain = prompt | asset_generator_tool
        result = await chain.ainvoke({
            "objective": charter.objective,
            "metric": f"{charter.metric_name} ({charter.metric_unit})",
            "asset_id": brief.id,
            "channel": brief.channel,
            "asset_type": brief.asset_type,
            "key_message": brief.key_message,
            "cta": brief.call_to_action,
        })

        return CreativeAsset(
            id=f"asset_final_{uuid.uuid4().hex[:8]}",
            asset_brief_id=brief.id,
            channel=brief.channel,
            headline=result.headline,
            body_copy=result.body_copy,
            visual_suggestion=result.visual_suggestion
        )

    except Exception as e:
        logger.error(f"  > Error generating creative for brief {brief.id}: {e}", exc_info=True)
        return None

async def generate_all_assets(state: CreativeAgentState) -> CreativeAgentState:
    """
    The main node of the agent. It orchestrates the generation of all creative assets
    defined in the strike plan's asset briefs.
    """
    logger.info("--- Node: Generating All Creative Assets ---")
    strike_plan = state['strike_plan']
    charter = state['outcome_charter']
    
    if not strike_plan.asset_briefs:
        logger.warning("  > No asset briefs found in the strike plan. Nothing to generate.")
        state['asset_package'] = AssetPackage(strike_plan_id=strike_plan.id, assets=[])
        return state

    # Create a list of async tasks to run in parallel
    generation_tasks = [generate_single_asset(brief, charter) for brief in strike_plan.asset_briefs]

    # Run all generation tasks concurrently
    generated_results = await asyncio.gather(*generation_tasks)

    # Filter out any tasks that failed (returned None)
    successful_assets = [result for result in generated_results if result is not None]

    if not successful_assets:
        state['error'] = "The AI failed to generate any creative assets from the briefs."
        return state

    state['asset_package'] = AssetPackage(
        strike_plan_id=strike_plan.id,
        assets=successful_assets
    )
    logger.info(f"  > Successfully generated {len(successful_assets)} creative assets.")
    return state

# --- Graph Definition ---
def build_creative_director_graph():
    """Builds and compiles the LangGraph for the creative director agent."""
    workflow = StateGraph(CreativeAgentState)
    workflow.add_node("generate_assets", generate_all_assets)
    workflow.set_entry_point("generate_assets")
    workflow.add_edge("generate_assets", END)
    return workflow.compile()

creative_director_graph = build_creative_director_graph()

# --- Main Agent Runner Function ---
async def run_creative_director_agent(strike_plan_dict: dict, outcome_charter_dict: dict) -> dict:
    """
    Entrypoint to run the creative director agent.
    Takes a strike plan and its charter, and returns a package of generated creative assets.
    """
    logger.info("--- Running Creative Director Agent ---")
    try:
        strike_plan = StrikePlan(**strike_plan_dict)
        outcome_charter = OutcomeCharter(**outcome_charter_dict)
        
        initial_state = {
            "strike_plan": strike_plan,
            "outcome_charter": outcome_charter
        }

        final_state = await creative_director_graph.ainvoke(initial_state)

        if final_state.get('error'):
            logger.error(f"  > Agent finished with error: {final_state['error']}")
            return {"error": final_state['error']}

        logger.info("  > Agent finished successfully.")
        return final_state['asset_package'].model_dump()
        
    except Exception as e:
        logger.error(f"  > Critical error running creative director agent: {e}", exc_info=True)
        return {"error": "A critical error occurred while setting up the creative director agent."}

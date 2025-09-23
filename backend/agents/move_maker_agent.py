import uuid
import logging
import json
from datetime import datetime, timedelta
from typing import TypedDict

from pydantic import BaseModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama.chat_models import ChatOllama
from langgraph.graph import StateGraph, END

from core.config import settings
from services.registry import get_services
from schemas.cohort_schemas import EnrichedCohort
from schemas.outcome_schemas import OutcomeCharter
from schemas.move_schemas import StrikePlan

# --- Configuration & Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Models ---
# This is a highly strategic task that requires the best reasoning model.
def _get_reasoning_llm() -> ChatOllama:
    try:
        return get_services().llm_reasoning
    except Exception:
        return ChatOllama(model=settings.OLLAMA_REASONING_MODEL, temperature=0.3, base_url=settings.OLLAMA_BASE_URL)


# --- Agent State ---
class MoveMakerAgentState(TypedDict):
    """
    Defines the state for the Move Maker graph.
    It takes a charter and cohort, and produces a complete strike plan.
    """
    outcome_charter: OutcomeCharter
    target_cohort: EnrichedCohort
    strike_plan: StrikePlan | None
    error: str | None


# --- Pydantic Models for Structured LLM Outputs (Tools) ---
# The LLM will be forced to output a valid StrikePlan object.
class StrikePlanTool(BaseModel):
    """A tool for the LLM to output a complete and actionable Strike Plan."""
    plan: StrikePlan


# --- Agent Nodes ---
def generate_strike_plan(state: MoveMakerAgentState) -> MoveMakerAgentState:
    """
    The core node of the agent. It uses the reasoning LLM to 'explode' a charter
    into a detailed, actionable plan.
    """
    logger.info("--- Node: Generating Strike Plan ---")

    try:
        strike_plan_generator_tool = _get_reasoning_llm().with_structured_output(StrikePlanTool)
        charter = state['outcome_charter']
        cohort = state['target_cohort']

        strategies_summary = "\n".join(
            [f"- **{s.headline}**: {s.description} (Suggested Message: '{s.suggested_message}')" for s in cohort.strategies]
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system",
             "You are an expert marketing operations manager and tactician. Your job is to take a high-level Outcome Charter and a customer cohort profile and create a detailed, day-by-day Strike Plan for the specified time window. "
             "The plan must be practical, actionable, and directly aimed at achieving the charter's target metric.\n\n"
             "Follow this process:\n"
             "1.  **Deconstruct the Objective**: Break the charter's objective into 2-3 smaller, testable experiments. Each experiment needs a clear hypothesis.\n"
             "2.  **Define Creative Needs**: For each experiment, define the necessary creative assets. What videos, images, or text posts are needed? Create a concise brief for each.\n"
             "3.  **Build the Schedule**: Create a day-by-day calendar of actions for the entire campaign window. Be specific about what happens each day (e.g., 'Publish Instagram Reel', 'Send WhatsApp broadcast to 50 users').\n"
             "4.  **Ensure Coherence**: The experiments, assets, and schedule must all logically connect to the suggested strategies and the overall objective.\n"
             "5.  **Adhere to the Schema**: Use the 'StrikePlanTool' to format your entire response. Ensure all IDs are unique and descriptive (e.g., 'exp_promo_video', 'asset_reel_1')."),
            ("human",
             "Please generate a Strike Plan based on the following information:\n\n"
             "**Target Cohort**: {cohort_name} ({icp_label})\n"
             "**Marketing Strategies Brainstormed for this Cohort**:\n{strategies_summary}\n\n"
             "**The Approved Outcome Charter to Execute**:\n"
             "```json\n{charter_json}\n```\n\n"
             "Now, create the complete Strike Plan.")
        ])

        chain = prompt | strike_plan_generator_tool
        
        # Calculate start and end dates for the LLM to use
        today = datetime.now()
        start_date = today + timedelta(days=1)
        end_date = start_date + timedelta(days=charter.time_window_days)
        
        charter_dict = charter.dict()
        charter_dict['start_date'] = start_date.strftime("%Y-%m-%d")
        charter_dict['end_date'] = end_date.strftime("%Y-%m-%d")


        result = chain.invoke({
            "cohort_name": cohort.cohort_details.name,
            "icp_label": cohort.icp_card.label,
            "strategies_summary": strategies_summary,
            "charter_json": json.dumps(charter_dict)
        })

        # Finalize the plan with server-side details
        strike_plan = result.plan
        strike_plan.id = f"plan_{uuid.uuid4().hex[:8]}"
        strike_plan.outcome_charter_id = charter.id
        strike_plan.target_cohort_name = cohort.cohort_details.name
        
        state['strike_plan'] = strike_plan
        logger.info(f"  > Successfully generated Strike Plan with ID: {strike_plan.id}")
        return state

    except Exception as e:
        logger.error(f"  > Error in strike plan generation node: {e}", exc_info=True)
        state['error'] = "The AI failed to generate a tactical strike plan. The reasoning model might have had an issue with the complexity of the request."
        return state


# --- Graph Definition ---
def build_move_maker_graph():
    """Builds and compiles the LangGraph for the move maker agent."""
    workflow = StateGraph(MoveMakerAgentState)
    workflow.add_node("generate_strike_plan", generate_strike_plan)
    workflow.set_entry_point("generate_strike_plan")
    workflow.add_edge("generate_strike_plan", END)
    return workflow.compile()

move_maker_graph = build_move_maker_graph()


# --- Main Agent Runner Function ---
async def run_move_maker_agent(outcome_charter_dict: dict, target_cohort_dict: dict) -> dict:
    """
    Entrypoint to run the move maker agent.
    Takes an outcome charter and a cohort, returns a complete strike plan.
    """
    logger.info("--- Running Move Maker Agent ---")
    try:
        outcome_charter = OutcomeCharter(**outcome_charter_dict)
        target_cohort = EnrichedCohort(**target_cohort_dict)

        initial_state = {
            "outcome_charter": outcome_charter,
            "target_cohort": target_cohort
        }

        final_state = await move_maker_graph.ainvoke(initial_state)

        if final_state.get('error'):
            logger.error(f"  > Agent finished with error: {final_state['error']}")
            return {"error": final_state['error']}

        logger.info("  > Agent finished successfully.")
        return final_state['strike_plan'].model_dump()
        
    except Exception as e:
        logger.error(f"  > Critical error running move maker agent: {e}", exc_info=True)
        return {"error": "A critical error occurred while setting up the move maker agent."}

import uuid
import logging
from typing import TypedDict, List

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_ollama.chat_models import ChatOllama
from langgraph.graph import StateGraph, END

from core.config import settings
from services.registry import get_services
from schemas.cohort_schemas import EnrichedCohort
from schemas.outcome_schemas import OutcomeCharter

# --- Configuration & Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Models ---
# The reasoning model is essential for this strategic planning task.
def _get_reasoning_llm() -> ChatOllama:
    try:
        return get_services().llm_reasoning
    except Exception:
        return ChatOllama(model=settings.OLLAMA_REASONING_MODEL, temperature=0.2, base_url=settings.OLLAMA_BASE_URL)


# --- Agent State ---
class OutcomeAgentState(TypedDict):
    """
    Defines the state for the outcome commitment graph.
    It takes a high-level goal and a cohort, and produces a draft charter.
    """
    high_level_goal: str
    target_cohort: EnrichedCohort
    draft_charter: OutcomeCharter | None
    error: str | None


# --- Pydantic Models for Structured LLM Outputs (Tools) ---
class DraftCharterTool(BaseModel):
    """A tool for the LLM to output a well-defined, draft OutcomeCharter."""
    charter: OutcomeCharter = Field(description="The complete, detailed, and measurable Outcome Charter.")


# --- Agent Nodes ---
def draft_outcome_charter(state: OutcomeAgentState) -> OutcomeAgentState:
    """
    The core node of the agent. It translates a fuzzy user goal into a specific,
    structured OutcomeCharter using the reasoning LLM.
    """
    logger.info("--- Node: Drafting Outcome Charter ---")

    try:
        charter_drafter_tool = _get_reasoning_llm().with_structured_output(DraftCharterTool)

        cohort = state['target_cohort']
        goal = state['high_level_goal']
        
        # Prepare a detailed summary of the cohort and their strategies for the prompt
        strategies_summary = "\n".join(
            [f"- {s.headline}: {s.description}" for s in cohort.strategies]
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system",
             "You are a data-driven Chief Marketing Officer (CMO) with expertise in setting OKRs (Objectives and Key Results) for growth experiments. "
             "Your task is to take a high-level marketing goal and a detailed customer cohort profile, and translate them into a single, specific, measurable, and time-bound Outcome Charter.\n\n"
             "Follow this thought process:\n"
             "1.  **Objective**: Rephrase the user's goal into a clear, concise objective statement.\n"
             "2.  **Metric (OMTM)**: Identify the SINGLE most important metric (The One Metric That Matters) that directly measures the success of the objective. For a food business, this is often related to 'orders', 'revenue', or 'signups'. Avoid vanity metrics.\n"
             "3.  **Baseline & Target**: Propose realistic baseline and target numbers. Since you don't have real data, make educated guesses. For a local cohort of ~5000 people, a baseline might be 10-20 orders a day. A good target is a 15-30% lift.\n"
             "4.  **Time Window**: Propose a short, focused time window, typically 14 or 30 days, for the campaign.\n"
             "5.  **Funnel Stage**: Classify the objective into the AARRR framework (Acquisition, Activation, Retention, Referral, Revenue).\n"
             "6.  **Guardrails**: Suggest sensible starting guardrails, like a budget cap.\n\n"
             "Use the 'DraftCharterTool' to format your entire response."),
            ("human",
             "Here is the target cohort we are focusing on:\n"
             "**Cohort Name**: {cohort_name}\n"
             "**ICP Label**: {icp_label}\n"
             "**ICP Pain Point**: {icp_pain_point}\n"
             "**Suggested Strategies**:\n{strategies_summary}\n\n"
             "The high-level marketing goal for this cohort is: **'{goal}'**\n\n"
             "Please draft a complete Outcome Charter based on this information.")
        ])

        chain = prompt | charter_drafter_tool
        
        # The charter ID will be set by the tool, but we can provide a placeholder
        # In a real system, this would be handled by the database.
        unique_id = f"charter_{uuid.uuid4().hex[:8]}"

        result = chain.invoke({
            "cohort_name": cohort.cohort_details.name,
            "icp_label": cohort.icp_card.label,
            "icp_pain_point": cohort.icp_card.primary_pain_point,
            "strategies_summary": strategies_summary,
            "goal": goal
        })
        
        # Finalize the charter with server-side details
        draft_charter = result.charter
        draft_charter.id = unique_id
        draft_charter.target_cohort_id = cohort.cohort_details.id
        draft_charter.status = "draft"
        
        state['draft_charter'] = draft_charter
        logger.info(f"  > Successfully drafted charter '{draft_charter.objective}' with ID: {draft_charter.id}")
        return state

    except Exception as e:
        logger.error(f"  > Error in charter drafting node: {e}", exc_info=True)
        state['error'] = "The AI failed to draft a strategic charter. The reasoning model might be experiencing issues or the input was ambiguous."
        return state

# --- Graph Definition ---
def build_outcome_committer_graph():
    """Builds and compiles the LangGraph for the outcome committer agent."""
    workflow = StateGraph(OutcomeAgentState)
    # Node name must not clash with a state key; use a distinct name
    workflow.add_node("draft_charter_node", draft_outcome_charter)
    workflow.set_entry_point("draft_charter_node")
    workflow.add_edge("draft_charter_node", END)
    return workflow.compile()

outcome_committer_graph = build_outcome_committer_graph()

# --- Main Agent Runner Function ---
async def run_outcome_committer_agent(high_level_goal: str, target_cohort_dict: dict) -> dict:
    """
    Entrypoint to run the outcome committer agent.
    Takes a high-level goal and a target cohort, and returns a draft charter.
    """
    logger.info("--- Running Outcome Committer Agent ---")
    try:
        target_cohort = EnrichedCohort(**target_cohort_dict)
        initial_state = {
            "high_level_goal": high_level_goal,
            "target_cohort": target_cohort
        }

        # Asynchronously invoke the graph
        final_state = await outcome_committer_graph.ainvoke(initial_state)

        if final_state.get('error'):
            logger.error(f"  > Agent finished with error: {final_state['error']}")
            return {"error": final_state['error']}

        logger.info("  > Agent finished successfully.")
        return final_state['draft_charter'].model_dump()
        
    except Exception as e:
        logger.error(f"  > Critical error running outcome committer agent: {e}", exc_info=True)
        return {"error": "A critical error occurred while setting up the outcome committer agent."}

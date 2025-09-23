import uuid
import logging
from typing import TypedDict, List

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_ollama.chat_models import ChatOllama
from langgraph.graph import StateGraph, END
import asyncio

from core.config import settings
from services.registry import get_services
from schemas.icp_schemas import ICPReport, ICPCard, Cohort
from schemas.cohort_schemas import CohortStrategy, EnrichedCohort, CohortStrategyReport

# --- Configuration & Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Models ---
def _get_reasoning_llm() -> ChatOllama:
    try:
        return get_services().llm_reasoning
    except Exception:
        return ChatOllama(model=settings.OLLAMA_REASONING_MODEL, temperature=0.5, base_url=settings.OLLAMA_BASE_URL)

# --- Agent State ---
class CohortAgentState(TypedDict):
    """
    Defines the state for the cohort enrichment graph.
    It takes an ICP report and produces an enriched cohort strategy report.
    """
    icp_report: ICPReport
    cohort_strategy_report: CohortStrategyReport | None
    error: str | None

# --- Pydantic Models for Structured LLM Outputs (Tools) ---
class GeneratedStrategies(BaseModel):
    """A tool for the LLM to output a list of generated marketing strategies for a single cohort."""
    strategies: List[CohortStrategy] = Field(
        description="A list of 2-3 distinct marketing strategies for the specified customer cohort.",
        default_factory=list
    )

# --- Agent Node ---
async def enrich_single_cohort(cohort: Cohort, icp: ICPCard) -> EnrichedCohort | None:
    """
    An async helper function to process a single cohort. This allows us to run multiple enrichments in parallel.
    """
    logger.info(f"--- Enriching Cohort: {cohort.name} ---")
    try:
        strategy_generator_tool = _get_reasoning_llm().with_structured_output(GeneratedStrategies)

        prompt = ChatPromptTemplate.from_messages([
            ("system",
             "You are a Senior Growth Marketer specializing in hyper-local campaigns in India for food & beverage businesses. "
             "Your task is to generate 2-3 distinct, creative, and actionable marketing strategies for a specific customer cohort. "
             "For each strategy, provide a catchy headline, a short description, and a sample marketing message.\n\n"
             "Key considerations:\n"
             "- Be highly specific to the ICP's pain points and context.\n"
             "- Think about low-cost, high-impact local tactics.\n"
             "- The message should be ready to use for an ad, social media post, or flyer.\n\n"
             "Use the 'GeneratedStrategies' tool to format your entire response."),
            ("human",
             "Please generate marketing strategies for the following cohort:\n\n"
             "**Cohort Name**: {cohort_name}\n"
             "**Linked Ideal Customer Profile (ICP)**:\n"
             " - **Label**: {icp_label}\n"
             " - **Pain Point**: {icp_pain_point}\n"
             " - **Primary Channels**: {icp_channels}\n"
             " - **Opportunity Window**: {icp_window}\n\n"
             "Generate your strategies based on this information.")
        ])

        chain = prompt | strategy_generator_tool
        result = await chain.ainvoke({
            "cohort_name": cohort.name,
            "icp_label": icp.label,
            "icp_pain_point": icp.primary_pain_point,
            "icp_channels": ", ".join(icp.primary_channels),
            "icp_window": icp.opportunity_window,
        })

        # Assign unique IDs to each generated strategy
        for strategy in result.strategies:
            strategy.id = f"strat_{uuid.uuid4().hex[:8]}"

        return EnrichedCohort(
            cohort_details=cohort,
            icp_card=icp,
            strategies=result.strategies
        )

    except Exception as e:
        logger.error(f"  > Error enriching cohort {cohort.name}: {e}", exc_info=True)
        return None


async def generate_cohort_strategies(state: CohortAgentState) -> CohortAgentState:
    """
    The main node of the agent. It orchestrates the enrichment of all cohorts from the input report.
    """
    logger.info("--- Node: Generating Cohort Strategies ---")
    icp_report = state['icp_report']
    
    # Create a mapping of ICP IDs to ICP Cards for easy lookup
    icp_map = {icp.id: icp for icp in icp_report.icp_cards}

    # Create a list of async tasks to run in parallel
    enrichment_tasks = []
    for cohort in icp_report.cohorts:
        linked_icp = icp_map.get(cohort.icp_id)
        if linked_icp:
            enrichment_tasks.append(enrich_single_cohort(cohort, linked_icp))
        else:
            logger.warning(f"  > Cohort '{cohort.name}' has a missing or invalid ICP ID: '{cohort.icp_id}'. Skipping.")

    if not enrichment_tasks:
        state['error'] = "No valid cohorts were found to process."
        return state

    # Run all enrichment tasks concurrently
    enriched_results = await asyncio.gather(*enrichment_tasks)

    # Filter out any tasks that failed (returned None)
    successful_enrichments = [result for result in enriched_results if result is not None]

    if not successful_enrichments:
        state['error'] = "The AI failed to generate strategies for all provided cohorts."
        return state

    state['cohort_strategy_report'] = CohortStrategyReport(enriched_cohorts=successful_enrichments)
    logger.info(f"  > Successfully enriched {len(successful_enrichments)} cohorts with new strategies.")
    return state


# --- Graph Definition ---
def build_cohort_strategist_graph():
    """Builds and compiles the LangGraph for the cohort strategist agent."""
    workflow = StateGraph(CohortAgentState)
    workflow.add_node("generate_strategies", generate_cohort_strategies)
    workflow.set_entry_point("generate_strategies")
    workflow.add_edge("generate_strategies", END)
    return workflow.compile()

cohort_strategist_graph = build_cohort_strategist_graph()


# --- Main Agent Runner Function ---
async def run_cohort_strategist_agent(icp_report_dict: dict) -> dict:
    """
    Entrypoint to run the cohort strategist agent.
    Takes an ICP report and returns a report with enriched cohorts.
    """
    logger.info("--- Running Cohort Strategist Agent ---")
    try:
        icp_report = ICPReport(**icp_report_dict)
        initial_state = {"icp_report": icp_report}

        # Asynchronously invoke the graph
        final_state = await cohort_strategist_graph.ainvoke(initial_state)

        if final_state.get('error'):
            logger.error(f"  > Agent finished with error: {final_state['error']}")
            return {"error": final_state['error']}

        logger.info("  > Agent finished successfully.")
        return final_state['cohort_strategy_report'].model_dump()
        
    except Exception as e:
        logger.error(f"  > Critical error running cohort strategist agent: {e}", exc_info=True)
        return {"error": "A critical error occurred while setting up the cohort strategist agent."}

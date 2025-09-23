import uuid
import logging
from typing import TypedDict, List

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_ollama.chat_models import ChatOllama
from langgraph.graph import StateGraph, END

from core.config import settings
from services.registry import get_services
from schemas.geo_schemas import MarketNeedReport, GeoSignal
from schemas.icp_schemas import ICPCard, Cohort, ICPReport

# --- Configuration & Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Models ---
# The reasoning model is best for this kind of creative/strategic generation task.
def _get_reasoning_llm() -> ChatOllama:
    try:
        return get_services().llm_reasoning
    except Exception:
        return ChatOllama(model=settings.OLLAMA_REASONING_MODEL, temperature=0.4, base_url=settings.OLLAMA_BASE_URL)


# --- Agent State ---
class ICPBuilderAgentState(TypedDict):
    """
    Defines the state for the ICP generation graph.
    It takes a market report and produces an ICP report.
    """
    market_report: MarketNeedReport
    icp_report: ICPReport | None
    error: str | None


# --- Pydantic Models for Structured LLM Outputs (Tools) ---
class GeneratedICPs(BaseModel):
    """A tool for the LLM to output a list of generated ICP cards and cohorts."""
    generated_icps_and_cohorts: List[ICPCard] = Field(description="A list of detailed Ideal Customer Profile cards based on the provided geo-data.")


# --- Agent Nodes ---

def generate_icps_and_cohorts(state: ICPBuilderAgentState) -> ICPBuilderAgentState:
    """
    This is the core node of the agent. It takes the demand hotspots from the
    market analysis and uses the reasoning LLM to generate rich ICPs.
    """
    logger.info("--- Node: Generating ICPs and Cohorts ---")
    
    market_report = state['market_report']
    
    # If there are no hot demand spots, we can't generate ICPs.
    if not market_report.demand_hotspots:
        logger.warning("  > No demand hotspots found. Skipping ICP generation.")
        state['icp_report'] = ICPReport(icp_cards=[], cohorts=[])
        return state

    try:
        icp_generator_tool = _get_reasoning_llm().with_structured_output(GeneratedICPs)

        # We create a simplified text representation of the hotspots for the prompt.
        hotspots_summary = "\n".join(
            [f"- {hotspot.poi_type.capitalize()} named '{hotspot.poi_name}' with an estimated {hotspot.headcount} people and a reach score of {hotspot.reach_score:.0f}."
             for hotspot in market_report.demand_hotspots]
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system",
             "You are a world-class market strategist specializing in the Indian market. Your task is to create detailed, actionable Ideal Customer Profiles (ICPs) and marketing cohorts based on raw geo-demographic data for a new food business (e.g., a cloud kitchen or a cafe).\n\n"
             "Follow these steps for each demand hotspot provided:\n"
             "1.  **Create a Label**: Give a catchy, descriptive label (e.g., 'Tech Park Lunchers - DLF Cybercity', 'Evening Study Group - IIT Madras Students').\n"
             "2.  **Estimate Size**: Use the provided headcount as the size estimate.\n"
             "3.  **Define the Primary Pain Point**: Infer the most likely need. For office workers, it might be a 'quick, healthy, and affordable lunch'. For students, it could be 'late-night study snacks that aren't too expensive'. Be specific.\n"
             "4.  **Identify the Opportunity Window**: Suggest the best times to target them (e.g., 'Weekdays 12:30-14:30', 'Weekends 19:00-22:00').\n"
             "5.  **Suggest Primary Channels**: Recommend 2-3 realistic marketing channels. Think local: 'Local flyers near campus', 'Partnerships with corporate cafeterias', 'Targeted Instagram ads for the geo-location'.\n"
             "6.  **Craft a Proof Hook**: Write a compelling, believable marketing claim that could be used in an ad, e.g., 'The 15-minute lunch solution for busy professionals at Tidel Park.'\n\n"
             "Use the 'GeneratedICPs' tool to format your entire response."),
            ("human",
             "Here are the demand hotspots identified in Chennai:\n{hotspots_summary}\n\n"
             "Please generate the ICP cards based on this data.")
        ])

        chain = prompt | icp_generator_tool
        result = chain.invoke({"hotspots_summary": hotspots_summary})

        generated_cards = result.generated_icps_and_cohorts
        all_cohorts = []
        
        # Post-process to add unique IDs and create corresponding cohorts
        for card in generated_cards:
            card_id = f"icp_{uuid.uuid4().hex[:8]}"
            card.id = card_id
            
            cohort_id = f"coh_{uuid.uuid4().hex[:8]}"
            cohort_name = card.label.lower().replace(" ", "_").replace("-", "").replace("'", "")
            
            new_cohort = Cohort(
                id=cohort_id,
                name=cohort_name,
                description=f"Actionable cohort for the '{card.label}' ICP.",
                icp_id=card_id,
                activation_rules=f"Geo-fence around the POI; Target during '{card.opportunity_window}' on channels: {', '.join(card.primary_channels)}"
            )
            all_cohorts.append(new_cohort)
            
        state['icp_report'] = ICPReport(icp_cards=generated_cards, cohorts=all_cohorts)
        logger.info(f"  > Successfully generated {len(generated_cards)} ICP cards and {len(all_cohorts)} cohorts.")
        return state

    except Exception as e:
        logger.error(f"  > Error in ICP generation node: {e}", exc_info=True)
        state['error'] = "The AI failed to generate ICPs from the market data. The reasoning model may be overloaded or the input was unusual."
        return state

# --- Graph Definition ---
def build_icp_builder_graph():
    """Builds and compiles the LangGraph for the ICP builder agent."""
    workflow = StateGraph(ICPBuilderAgentState)
    workflow.add_node("generate_icps", generate_icps_and_cohorts)
    workflow.set_entry_point("generate_icps")
    workflow.add_edge("generate_icps", END)
    return workflow.compile()

icp_builder_graph = build_icp_builder_graph()


# --- Main Agent Runner Function ---
async def run_icp_builder_agent(market_report_dict: dict) -> dict:
    """
    Entrypoint to run the ICP builder agent.
    Takes a market report and returns a dictionary of ICPs and cohorts.
    """
    logger.info("--- Running Geo-Aware ICP Builder Agent ---")
    try:
        market_report = MarketNeedReport(**market_report_dict)
        initial_state = {"market_report": market_report}

        # Asynchronously invoke the graph
        final_state = await icp_builder_graph.ainvoke(initial_state)

        if final_state.get('error'):
            logger.error(f"  > Agent finished with error: {final_state['error']}")
            return {"error": final_state['error']}

        logger.info("  > Agent finished successfully.")
        return final_state['icp_report'].model_dump()
        
    except Exception as e:
        logger.error(f"  > Critical error running ICP builder agent: {e}", exc_info=True)
        return {"error": "A critical error occurred while setting up the ICP builder agent."}

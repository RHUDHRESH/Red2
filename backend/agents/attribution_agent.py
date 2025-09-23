import uuid
import logging
from typing import TypedDict, List
from collections import defaultdict

from langgraph.graph import StateGraph, END

from schemas.launch_schemas import CampaignSimulationReport
from schemas.attribution_schemas import AttributionEvent, ProofArtifact, AttributionReport

# --- Configuration & Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Agent State ---
class AttributionAgentState(TypedDict):
    """
    Defines the state for the attribution graph.
    It takes a simulation report and produces a final attribution report.
    """
    simulation_report: CampaignSimulationReport
    attribution_report: AttributionReport | None
    error: str | None

# --- Agent Node ---
def process_events_and_build_report(state: AttributionAgentState) -> AttributionAgentState:
    """
    This is a deterministic node that acts as a data processor. It takes the raw event
    stream from the simulation and calculates final attribution metrics.
    """
    logger.info("--- Node: Processing Events and Building Attribution Report ---")
    try:
        sim_report = state['simulation_report']
        events: List[AttributionEvent] = sim_report.events

        if not events:
            state['error'] = "No events found in the simulation report to attribute."
            logger.warning("  > No events to process.")
            return state

        # --- Metric Calculation ---
        total_revenue = 0.0
        total_orders = 0
        revenue_by_channel = defaultdict(float)
        order_event_ids = []

        for event in events:
            if event.event_name == "order_placed":
                total_orders += 1
                total_revenue += event.revenue
                revenue_by_channel[event.channel] += event.revenue
                order_event_ids.append(event.event_id)

        # --- Proof Pack Generation ---
        proof_pack: List[ProofArtifact] = []

        # Create a proof artifact for the total orders
        if total_orders > 0:
            orders_proof = ProofArtifact(
                claim=f"Generated {total_orders} total paid orders.",
                supporting_event_ids=order_event_ids,
                source_summary="Derived from simulated 'order_placed' events in the campaign log."
            )
            proof_pack.append(orders_proof)

        # Create a proof artifact for the total revenue
        if total_revenue > 0:
            revenue_proof = ProofArtifact(
                claim=f"Generated ₹{total_revenue:,.2f} in total revenue.",
                supporting_event_ids=order_event_ids, # The same events prove revenue
                source_summary="Calculated by summing the 'revenue' field from all simulated 'order_placed' events."
            )
            proof_pack.append(revenue_proof)


        # --- Final Report Assembly ---
        attribution_report = AttributionReport(
            id=f"attr_{uuid.uuid4().hex[:8]}",
            strike_plan_id=sim_report.strike_plan_id,
            total_revenue=total_revenue,
            total_orders=total_orders,
            revenue_by_channel=dict(revenue_by_channel),
            proof_pack=proof_pack
        )

        state['attribution_report'] = attribution_report
        logger.info(f"  > Successfully built attribution report. Total Orders: {total_orders}, Total Revenue: ₹{total_revenue:.2f}")
        return state

    except Exception as e:
        logger.error(f"  > Error while building attribution report: {e}", exc_info=True)
        state['error'] = "A critical error occurred during data processing for the attribution report."
        return state


# --- Graph Definition ---
def build_attribution_graph():
    """Builds and compiles the LangGraph for the attribution agent."""
    workflow = StateGraph(AttributionAgentState)
    workflow.add_node("process_events", process_events_and_build_report)
    workflow.set_entry_point("process_events")
    workflow.add_edge("process_events", END)
    return workflow.compile()

attribution_graph = build_attribution_graph()

# --- Main Agent Runner Function ---
async def run_attribution_agent(sim_report_dict: dict) -> dict:
    """
    Entrypoint to run the attribution agent.
    """
    logger.info("--- Running Attribution & Proof Agent ---")
    try:
        sim_report = CampaignSimulationReport(**sim_report_dict)
        initial_state = {"simulation_report": sim_report}

        # Asynchronously invoke the graph
        final_state = await attribution_graph.ainvoke(initial_state)

        if final_state.get('error'):
            logger.error(f"  > Agent finished with error: {final_state['error']}")
            return {"error": final_state['error']}

        logger.info("  > Agent finished successfully.")
        return final_state['attribution_report'].model_dump()

    except Exception as e:
        logger.error(f"  > Critical error running attribution agent: {e}", exc_info=True)
        return {"error": "A critical error occurred while setting up the attribution agent."}

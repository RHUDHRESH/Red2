import uuid
import logging
import random
from datetime import datetime, timedelta
from typing import TypedDict, List
import asyncio

from langgraph.graph import StateGraph, END

from schemas.scheduler_schemas import SchedulePackage, ScheduledJob
from schemas.creative_schemas import AssetPackage
from schemas.launch_schemas import Contact, LaunchReport

# --- Configuration & Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Agent State ---
class LaunchAgentState(TypedDict):
    """
    Defines the state for the launch and nurture simulation graph.
    """
    schedule_package: SchedulePackage
    asset_package: AssetPackage
    contacts: List[Contact]
    campaign_log: List[str]
    launch_report: LaunchReport | None
    error: str | None

# --- Simulation Parameters ---
SIMULATED_COHORT_SIZE = 150  # Let's assume a cohort size for the simulation
SIMULATED_OPEN_RATE = 0.40   # 40% of users open the message
SIMULATED_CLICK_RATE = 0.15  # 15% of users who open also click

# --- Agent Nodes ---

def initialize_campaign(state: LaunchAgentState) -> LaunchAgentState:
    """
    Node 1: Kicks off the simulation. Creates a set of dummy contacts for the campaign.
    """
    logger.info("--- Node: Initializing Campaign Simulation ---")
    try:
        strike_plan_id = state['schedule_package'].strike_plan_id
        log = [f"[{datetime.utcnow().isoformat()}] START Campaign Simulation for Strike Plan: {strike_plan_id}"]
        
        # In a real system, this would fetch contacts from a DB. Here, we generate them.
        contacts = []
        for i in range(SIMULATED_COHORT_SIZE):
            contacts.append(Contact(
                id=f"sim_contact_{uuid.uuid4().hex[:8]}",
                cohort_id="simulated_cohort", # This would come from the strike plan
                channel_handle=f"user_{i+1}@example.com"
            ))
        
        log.append(f"[{datetime.utcnow().isoformat()}] Generated {len(contacts)} simulated contacts for the target cohort.")
        
        state['contacts'] = contacts
        state['campaign_log'] = log
        return state
        
    except Exception as e:
        logger.error(f"  > Error initializing campaign: {e}", exc_info=True)
        state['error'] = "Failed to initialize the campaign simulation."
        return state


def execute_launch_wave(state: LaunchAgentState) -> LaunchAgentState:
    """
    Node 2: Simulates the 'sending' of messages based on the schedule.
    """
    logger.info("--- Node: Executing Launch Wave ---")
    if state.get('error'): return state
    
    log = state['campaign_log']
    schedule = state['schedule_package']
    contacts = state['contacts']
    
    messages_sent = 0
    # We process jobs sorted by their scheduled time
    sorted_jobs = sorted(schedule.jobs, key=lambda j: j.publish_at_iso)

    for job in sorted_jobs:
        log.append(f"[{job.publish_at_iso}] EXECUTING JOB: {job.job_id} on channel '{job.channel}'")
        # Simulate sending this asset to every contact
        for contact in contacts:
            log.append(f"  - Sent asset {job.asset_id} to contact {contact.id} ({contact.channel_handle})")
            messages_sent += 1
    
    log.append(f"[{datetime.utcnow().isoformat()}] LAUNCH WAVE COMPLETE. Total messages sent: {messages_sent}")
    state['campaign_log'] = log
    return state


def simulate_engagement_and_nurture(state: LaunchAgentState) -> LaunchAgentState:
    """
    Node 3: Simulates user engagement (opens/clicks) and a simple nurture follow-up.
    """
    logger.info("--- Node: Simulating Engagement & Nurture ---")
    if state.get('error'): return state

    log = state['campaign_log']
    contacts = state['contacts']
    
    opened_contacts = random.sample(contacts, int(len(contacts) * SIMULATED_OPEN_RATE))
    clicked_contacts = random.sample(opened_contacts, int(len(opened_contacts) * SIMULATED_CLICK_RATE))

    log.append(f"[{datetime.utcnow().isoformat()}] ENGAGEMENT SIMULATION: {len(opened_contacts)} contacts opened, {len(clicked_contacts)} contacts clicked.")

    # Simple nurture sequence: send a follow-up to those who clicked
    if clicked_contacts:
        log.append(f"[{datetime.utcnow().isoformat()}] NURTURE: Sending follow-up to {len(clicked_contacts)} engaged contacts.")
        for contact in clicked_contacts:
            contact.engagement_score += 10 # Increase score for engaged users
            log.append(f"  - Sent nurture message to contact {contact.id}.")

    state['contacts'] = contacts
    state['campaign_log'] = log
    return state


def generate_final_report(state: LaunchAgentState) -> LaunchAgentState:
    """
    Node 4: Compiles the final report of the simulation.
    """
    logger.info("--- Node: Generating Final Report ---")
    if state.get('error'): return state
    
    log = state['campaign_log']
    contacts = state['contacts']
    messages_sent = len(contacts) * len(state['schedule_package'].jobs) # Simple calculation
    
    # Calculate simulated engagement rate based on initial send
    total_contacts = len(contacts)
    clicked_count = int(total_contacts * SIMULATED_OPEN_RATE * SIMULATED_CLICK_RATE)
    engagement_rate = (clicked_count / total_contacts) * 100 if total_contacts > 0 else 0

    report = LaunchReport(
        total_contacts_targeted=total_contacts,
        messages_sent=messages_sent,
        simulated_engagement_rate=round(engagement_rate, 2),
        log=log
    )
    
    log.append(f"[{datetime.utcnow().isoformat()}] END Campaign Simulation. Final Engagement Rate: {engagement_rate:.2f}%.")
    
    state['launch_report'] = report
    state['campaign_log'] = log # Finalize log
    logger.info("  > Final report generated successfully.")
    return state


# --- Graph Definition ---
def build_launch_agent_graph():
    """Builds and compiles the LangGraph for the launch and nurture agent."""
    workflow = StateGraph(LaunchAgentState)
    workflow.add_node("initialize_campaign", initialize_campaign)
    workflow.add_node("execute_launch_wave", execute_launch_wave)
    workflow.add_node("simulate_engagement", simulate_engagement_and_nurture)
    workflow.add_node("generate_report", generate_final_report)

    workflow.set_entry_point("initialize_campaign")
    workflow.add_edge("initialize_campaign", "execute_launch_wave")
    workflow.add_edge("execute_launch_wave", "simulate_engagement")
    workflow.add_edge("simulate_engagement", "generate_report")
    workflow.add_edge("generate_report", END)
    
    return workflow.compile()

launch_agent_graph = build_launch_agent_graph()

# --- Main Agent Runner Function ---
async def run_launch_agent(schedule_package_dict: dict, asset_package_dict: dict) -> dict:
    """
    Entrypoint to run the launch & nurture simulation agent.
    """
    logger.info("--- Running Launch & Nurture Agent ---")
    try:
        schedule_package = SchedulePackage(**schedule_package_dict)
        asset_package = AssetPackage(**asset_package_dict)
        
        initial_state = {
            "schedule_package": schedule_package,
            "asset_package": asset_package
        }

        final_state = await launch_agent_graph.ainvoke(initial_state)

        if final_state.get('error'):
            logger.error(f"  > Agent finished with error: {final_state['error']}")
            return {"error": final_state['error']}

        logger.info("  > Agent finished successfully.")
        return final_state['launch_report'].model_dump()
        
    except Exception as e:
        logger.error(f"  > Critical error running launch agent: {e}", exc_info=True)
        return {"error": "A critical error occurred while setting up the launch agent."}

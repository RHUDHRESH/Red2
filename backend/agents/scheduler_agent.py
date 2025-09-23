import uuid
import logging
from datetime import datetime, time
from typing import TypedDict, List
from zoneinfo import ZoneInfo

from langgraph.graph import StateGraph, END

from schemas.move_schemas import StrikePlan
from schemas.creative_schemas import AssetPackage, CreativeAsset
from schemas.scheduler_schemas import ScheduledJob, SchedulePackage

# --- Configuration & Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Agent State ---
class SchedulerAgentState(TypedDict):
    """
    Defines the state for the scheduling graph.
    It takes a strike plan and an asset package, and produces a final schedule package.
    """
    strike_plan: StrikePlan
    asset_package: AssetPackage
    schedule_package: SchedulePackage | None
    error: str | None

# --- Agent Node ---
def build_schedule_package(state: SchedulerAgentState) -> SchedulerAgentState:
    """
    This is a deterministic node. It does not use an LLM. Its job is to
    logically process the schedule from the strike plan and create a list
    of concrete, timed jobs.
    """
    logger.info("--- Node: Building Final Schedule Package ---")
    try:
        strike_plan = state['strike_plan']
        asset_package = state['asset_package']
        
        # Create a mapping of asset brief IDs to final creative asset IDs for easy lookup
        brief_to_asset_map: dict[str, CreativeAsset] = {}
        for asset in asset_package.assets:
            brief_to_asset_map[asset.asset_brief_id] = asset

        scheduled_jobs: List[ScheduledJob] = []
        
        # This is a critical mapping. We need to find which asset fulfills which scheduled action.
        # A more robust system might use a direct ID link. Here, we'll infer it.
        # We'll assume for now that the schedule's action_details gives a hint about the asset.
        for scheduled_action in strike_plan.schedule:
            # Find the corresponding asset by looking for a brief that matches the action's channel and description.
            # This is a simplification; a real system would have more direct links.
            target_asset = None
            for brief in strike_plan.asset_briefs:
                if brief.channel == scheduled_action.channel and brief.id in scheduled_action.action_details:
                    target_asset = brief_to_asset_map.get(brief.id)
                    break
            
            if not target_asset:
                logger.warning(f"  > Could not find a matching creative asset for scheduled action: '{scheduled_action.action_details}'. Skipping.")
                continue

            # Convert local time from plan to a UTC ISO 8601 timestamp
            # We assume the plan's timezone is Asia/Kolkata as per the blueprint
            try:
                local_tz = ZoneInfo("Asia/Kolkata")
                local_dt_str = f"{scheduled_action.date} {scheduled_action.time}"
                local_dt = datetime.strptime(local_dt_str, "%Y-%m-%d %H:%M")
                # Interpret parsed naive time as Asia/Kolkata local time
                local_dt_with_tz = local_dt.replace(tzinfo=local_tz)
                utc_dt = local_dt_with_tz.astimezone(ZoneInfo("UTC"))
                publish_at_iso = utc_dt.isoformat()
            except Exception as e:
                logger.error(f"  > Failed to parse date/time: {scheduled_action.date} {scheduled_action.time}. Error: {e}. Skipping job.")
                continue

            job = ScheduledJob(
                job_id=f"job_{uuid.uuid4().hex[:8]}",
                asset_id=target_asset.id,
                asset_headline=target_asset.headline,
                channel=scheduled_action.channel,
                publish_at_iso=publish_at_iso,
                status="scheduled"
            )
            scheduled_jobs.append(job)

        if not scheduled_jobs:
            state['error'] = "Could not create any scheduled jobs. Check if assets and schedule actions are properly linked."
            return state

        schedule_package = SchedulePackage(
            id=f"schpkg_{uuid.uuid4().hex[:8]}",
            strike_plan_id=strike_plan.id,
            jobs=scheduled_jobs
        )
        state['schedule_package'] = schedule_package
        logger.info(f"  > Successfully created schedule package with {len(scheduled_jobs)} jobs.")
        return state

    except Exception as e:
        logger.error(f"  > Error in building schedule package: {e}", exc_info=True)
        state['error'] = "A critical error occurred while building the final schedule."
        return state

# --- Graph Definition ---
def build_scheduler_graph():
    """Builds and compiles the LangGraph for the scheduler agent."""
    workflow = StateGraph(SchedulerAgentState)
    workflow.add_node("build_schedule", build_schedule_package)
    workflow.set_entry_point("build_schedule")
    workflow.add_edge("build_schedule", END)
    return workflow.compile()

scheduler_graph = build_scheduler_graph()

# --- Main Agent Runner Function ---
async def run_scheduler_agent(strike_plan_dict: dict, asset_package_dict: dict) -> dict:
    """
    Entrypoint to run the scheduler agent.
    """
    logger.info("--- Running Scheduler Agent ---")
    try:
        strike_plan = StrikePlan(**strike_plan_dict)
        asset_package = AssetPackage(**asset_package_dict)
        
        initial_state = {
            "strike_plan": strike_plan,
            "asset_package": asset_package
        }

        final_state = await scheduler_graph.ainvoke(initial_state)

        if final_state.get('error'):
            logger.error(f"  > Agent finished with error: {final_state['error']}")
            return {"error": final_state['error']}

        logger.info("  > Agent finished successfully.")
        return final_state['schedule_package'].model_dump()
        
    except Exception as e:
        logger.error(f"  > Critical error running scheduler agent: {e}", exc_info=True)
        return {"error": "A critical error occurred while setting up the scheduler agent."}

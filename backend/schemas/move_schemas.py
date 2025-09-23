from pydantic import BaseModel, Field
from typing import List, Dict, Any, Literal

class Experiment(BaseModel):
    """
    Defines a single marketing experiment within a Strike Plan.
    """
    id: str = Field(..., description="Unique ID for the experiment, e.g., exp_whatsapp_cta.")
    name: str = Field(..., description="A human-readable name for the experiment.")
    hypothesis: str = Field(..., description="The hypothesis being tested, in an 'If we do X, then Y will happen' format.")
    channels: List[str] = Field(..., description="The marketing channels involved, e.g., ['instagram_reels', 'whatsapp'].")
    mde_percent: float = Field(..., description="Minimum Detectable Effect as a percentage, e.g., 10.0 for a 10% lift.")

class AssetBrief(BaseModel):
    """
    Defines a request for a creative asset.
    """
    id: str = Field(..., description="Unique ID for the asset brief, e.g., asset_reel_speed_proof.")
    channel: str = Field(..., description="The channel this asset is for, e.g., 'instagram_reels'.")
    asset_type: Literal["video_brief", "image_brief", "text_post", "whatsapp_template"]
    key_message: str = Field(..., description="The single most important message the asset must convey.")
    call_to_action: str = Field(..., description="The desired action for the user to take.")

class ScheduledAction(BaseModel):
    """
    Defines a single action to be executed at a specific time.
    """
    date: str = Field(..., description="The scheduled date in YYYY-MM-DD format.")
    time: str = Field(..., description="The scheduled time in HH:MM format (Asia/Kolkata).")
    channel: str = Field(..., description="The channel for the action.")
    action_details: str = Field(..., description="A description of the action, e.g., 'Publish Reel from asset_reel_speed_proof'.")
    
class StrikePlan(BaseModel):
    """
    The complete, actionable marketing plan for a given Outcome Charter.
    This is the master output of the Move Maker Agent.
    """
    id: str = Field(..., description="Unique ID for the strike plan, e.g., move_college_lunch_q3.")
    outcome_charter_id: str = Field(..., description="The ID of the charter this plan is designed to achieve.")
    start_date: str = Field(..., description="The start date of the move in YYYY-MM-DD format.")
    end_date: str = Field(..., description="The end date of the move in YYYY-MM-DD format.")
    target_cohort_name: str
    experiments: List[Experiment]
    asset_briefs: List[AssetBrief]
    schedule: List[ScheduledAction]

from pydantic import BaseModel, Field
from typing import List, Literal

class ScheduledJob(BaseModel):
    """
    Represents a single, specific creative asset scheduled for publishing
    on a specific channel at a specific time.
    """
    job_id: str = Field(..., description="A unique ID for this scheduled job, e.g., job_123.")
    asset_id: str = Field(..., description="The ID of the creative asset to be published.")
    asset_headline: str | None = Field(default=None, description="The headline of the asset, for easy reference.")
    channel: str = Field(..., description="The channel to publish on, e.g., 'instagram_reels'.")
    publish_at_iso: str = Field(..., description="The exact date and time for publishing in ISO 8601 format (UTC).")
    status: Literal["scheduled", "published", "failed"] = Field(default="scheduled", description="The current status of the job.")

class SchedulePackage(BaseModel):
    """
    The final output of the Scheduler Agent. This is a complete package
    of all jobs ready for the campaign execution.
    """
    id: str = Field(..., description="A unique ID for this entire schedule package.")
    strike_plan_id: str = Field(..., description="The ID of the strike plan this schedule is based on.")
    jobs: List[ScheduledJob]

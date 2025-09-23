from pydantic import BaseModel, Field
from typing import List, Literal, Dict, Any
from datetime import datetime

class Contact(BaseModel):
    """
    Represents a single contact in a cohort.
    """
    id: str = Field(..., description="Unique ID for the contact, e.g., contact_123.")
    cohort_id: str = Field(..., description="The ID of the cohort this contact belongs to.")
    channel_handle: str = Field(..., description="The contact's handle on a specific channel, e.g., their email address or phone number.")
    status: Literal["active", "unsubscribed", "bounced"] = Field(default="active")
    engagement_score: int = Field(default=0, description="A score representing how engaged the contact is.")

class OutboundMessage(BaseModel):
    """
    Represents a single message sent to a contact as part of the campaign.
    """
    message_id: str
    contact_id: str
    asset_id: str
    channel: str
    sent_at: datetime
    status: Literal["sent", "delivered", "opened", "clicked", "failed"]

class CampaignLogEntry(BaseModel):
    """
    An entry in the campaign log, recording every action taken.
    """
    timestamp: datetime
    entry: str

class LaunchReport(BaseModel):
    """
    A summary report generated at the end of the launch simulation.
    """
    total_contacts_targeted: int
    messages_sent: int
    simulated_engagement_rate: float = Field(..., description="A simulated engagement rate, e.g., 15.0 for 15%.")
    log: List[str]

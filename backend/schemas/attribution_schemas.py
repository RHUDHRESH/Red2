from pydantic import BaseModel, Field
from typing import List, Literal, Dict

class AttributionEvent(BaseModel):
    """
    Represents a single, canonical event in our system, like a message being sent or a link being clicked.
    In a real system, this would come from webhooks or tracking pixels.
    """
    event_id: str
    event_name: Literal["message_sent", "message_delivered", "link_clicked", "order_placed"]
    timestamp: str = Field(description="ISO 8601 timestamp of the event.")
    channel: str
    cohort_id: str
    asset_id: str | None = None
    revenue: float = 0.0

class ProofArtifact(BaseModel):
    """
    Represents a piece of evidence supporting a claim.
    """
    claim: str = Field(description="The marketing claim, e.g., 'Generated 41 paid orders.'")
    supporting_event_ids: List[str] = Field(description="A list of event IDs that substantiate this claim.")
    source_summary: str = Field(description="A human-readable summary of where the data comes from.")

class AttributionReport(BaseModel):
    """
    The final output of the Attribution & Proof Agent.
    """
    id: str
    strike_plan_id: str
    total_revenue: float
    total_orders: int
    revenue_by_channel: Dict[str, float]
    proof_pack: List[ProofArtifact]

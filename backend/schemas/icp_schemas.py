from pydantic import BaseModel, Field
from typing import List, Literal

class ICPCard(BaseModel):
    """
    Represents a detailed Ideal Customer Profile based on a specific geo-demographic cluster.
    """
    id: str = Field(..., description="A unique identifier for this ICP card.")
    label: str = Field(..., description="A descriptive label, e.g., 'Tech Park Lunchers - Tidel Park'.")
    size_estimate: int = Field(..., description="Estimated population of this ICP.")
    primary_pain_point: str = Field(..., description="The main problem or need we are solving for them, e.g., 'Needs a quick, affordable, and tasty lunch under ₹150'.")
    opportunity_window: str = Field(..., description="The key timeframes for engagement, e.g., 'Weekdays 12:00-15:00 & 19:00-21:00'.")
    primary_channels: List[str] = Field(..., description="The most effective marketing channels to reach them, e.g., ['LinkedIn Ads', 'Local Flyers', 'Corporate Partnerships'].")
    proof_hook: str = Field(..., description="An ASCI-compliant claim to use in marketing, e.g., 'The 10-minute lunch break upgrade trusted by 500+ developers.'")

class Cohort(BaseModel):
    """
    Represents an actionable marketing cohort derived from an ICP.
    """
    id: str = Field(..., description="A unique identifier for this cohort.")
    name: str = Field(..., description="The name of the cohort, e.g., 'tidel_park_weekday_lunch_rush'.")
    description: str = Field(..., description="A brief description of who is in this cohort.")
    icp_id: str = Field(..., description="The ID of the parent ICP card.")
    activation_rules: str = Field(..., description="The rules for targeting this cohort, e.g., 'Time: Mon-Fri 12:00-15:00; Geo-fence: Tidel Park radius 1km'.")

class ICPReport(BaseModel):
    """
    The final output of the ICP Builder agent, containing all generated cards and cohorts.
    """
    icp_cards: List[ICPCard]
    cohorts: List[Cohort]

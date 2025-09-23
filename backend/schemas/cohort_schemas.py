from pydantic import BaseModel, Field
from typing import List
from .icp_schemas import Cohort, ICPCard

class CohortStrategy(BaseModel):
    """
    Defines a specific marketing strategy or angle for a cohort.
    """
    id: str = Field(..., description="Unique ID for the strategy.")
    headline: str = Field(..., description="A catchy headline for this marketing angle.")
    description: str = Field(..., description="A brief paragraph explaining the strategy.")
    suggested_message: str = Field(..., description="An example marketing message (e.g., an ad copy or a social media post).")

class EnrichedCohort(BaseModel):
    """
    Represents a cohort that has been analyzed and enriched with strategic ideas.
    """
    cohort_details: Cohort = Field(..., description="The original cohort data.")
    icp_card: ICPCard = Field(..., description="The ICP card linked to this cohort.")
    strategies: List[CohortStrategy] = Field(..., description="A list of AI-generated strategies for this cohort.")

class CohortStrategyReport(BaseModel):
    """
    The final output of the Cohort Strategist Agent.
    """
    enriched_cohorts: List[EnrichedCohort]

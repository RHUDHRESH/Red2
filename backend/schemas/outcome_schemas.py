from pydantic import BaseModel, Field
from typing import List, Literal, Optional

class OutcomeCharter(BaseModel):
    """
    Defines a single, measurable, time-bound marketing objective.
    This serves as the master plan for the Move Maker and subsequent agents.
    """
    id: str = Field(..., description="Unique ID for this charter.")
    objective: str = Field(..., description="The high-level goal in plain English.", example="Increase paid lunch orders from the college cohort.")
    
    # The One Metric That Matters (OMTM)
    metric_name: str = Field(..., description="The specific, primary metric to be measured.", example="Daily Paid Orders")
    metric_unit: str = Field(..., description="The unit of the metric (e.g., 'orders', 'signups', '₹').", example="orders")
    
    # Baseline and Target
    baseline: float = Field(..., description="The current value of the metric before the campaign starts.")
    target: float = Field(..., description="The desired value of the metric after the campaign.")
    
    # Time and Scope
    time_window_days: int = Field(..., description="The duration of the campaign in days.", example=14)
    target_cohort_id: str = Field(..., description="The ID of the primary cohort being targeted.")
    
    # Funnel Stage (AARRR)
    funnel_stage: Literal["Acquisition", "Activation", "Retention", "Referral", "Revenue"] = Field(..., description="The stage of the pirate funnel this objective targets.")
    
    # Guardrails
    budget_cap: Optional[float] = Field(None, description="The maximum spend allowed for this objective.")
    cac_ceiling: Optional[float] = Field(None, description="The maximum acceptable Customer Acquisition Cost.")
    
    # Statistical Plan
    mde: Optional[float] = Field(None, description="Minimum Detectable Effect for experiments under this objective.")
    
    status: Literal["draft", "committed", "completed", "failed"] = Field(default="draft", description="The current status of the charter.")

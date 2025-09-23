from pydantic import BaseModel, Field
from typing import List, Literal, Dict

class PlaybookTemplate(BaseModel):
    """
    Represents a complete, reusable marketing playbook derived from a successful campaign.
    This is the core data model for the Template Archive.
    """
    template_id: str = Field(..., description="Unique ID for the template, e.g., playbook_q3_college_lunch_promo.")
    template_version: str = Field(default="1.0.0", description="Semantic version for the template, e.g., 1.0.1.")
    status: Literal["draft", "active", "deprecated"] = Field(default="active")
    
    # --- Searchable Metadata ---
    move_type: str = Field(..., description="A high-level category for the playbook, e.g., 'New Customer Acquisition', 'Holiday Promotion'.")
    channels: List[str] = Field(..., description="Primary channels used in this playbook, e.g., ['instagram_reels', 'whatsapp'].")
    target_icp_labels: List[str] = Field(..., description="Keywords describing the target ICP, e.g., ['college_students', 'tech_park_employees'].")
    
    # --- Core Content ---
    description: str = Field(..., description="A human-readable description of what this playbook does and when to use it.")
    outcome_charter_template: Dict = Field(..., description="A template of the Outcome Charter, with placeholders for metrics.")
    strike_plan_template: Dict = Field(..., description="A template of the Strike Plan, with placeholders for dates and specific names.")
    
    # --- Performance Data ---
    source_strike_plan_id: str = Field(..., description="The ID of the successful strike plan this template was created from.")
    key_performance_metrics: Dict[str, str] = Field(..., description="A summary of the results that made this playbook successful, e.g., {'conversion_rate': '2.5%', 'revenue': '₹15,000'}.")

class NextMoveRecommendation(BaseModel):
    """
    Represents a recommendation for which playbook to use next.
    """
    recommended_template_id: str
    recommendation_reason: str
    confidence_score: float = Field(..., description="A score from 0.0 to 1.0 indicating the confidence in this recommendation.")

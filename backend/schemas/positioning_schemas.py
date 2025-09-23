from pydantic import BaseModel, Field
from typing import List, Literal

class PositioningOptionCard(BaseModel):
    """
    Defines the structure for a single, comprehensive positioning option.
    Based on the 'Example output card' from your blueprint.
    """
    one_word: str
    category: str
    tagline: str
    pillars: List[str]
    behavior_lever: str
    first_assets: List[str]
    risks: List[str]
    score: float = 0.0
    score_breakdown: dict = Field(default_factory=dict)
    is_compliant: bool = False
    compliance_notes: str = ""

class PositioningGenerationRequest(BaseModel):
    """
    Defines the input needed to generate positioning options.
    This would be the output from the Intake Interview.
    """
    facts: List[str]
    claims: List[str]
    taboos: List[str] = []

class PositioningResponse(BaseModel):
    """
    The final response from the Positioning Agent API.
    """
    options: List[PositioningOptionCard]


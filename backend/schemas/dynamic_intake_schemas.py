from __future__ import annotations

from typing import List, Optional, Literal, Dict
from pydantic import BaseModel, Field, HttpUrl


PersonaLabel = Literal[
    "technical_founder",
    "operator_founder",
    "marketer",
    "brick_mortar_owner",
    "student_maker",
    "unknown",
]

DigitalFootprint = Literal["low", "medium", "high"]


class IntakeHints(BaseModel):
    name: Optional[str] = None
    company: Optional[str] = None
    website: Optional[HttpUrl] = None
    linkedin_url: Optional[HttpUrl] = None
    twitter_handle: Optional[str] = None
    location: Optional[str] = None


class PersonaProfile(BaseModel):
    persona_label: PersonaLabel
    digital_footprint: DigitalFootprint = "medium"
    confidence: float = 0.5
    notes: str = ""


class DynamicStartRequest(BaseModel):
    hints: IntakeHints = Field(default_factory=IntakeHints)


class DynamicStartResponse(BaseModel):
    persona: PersonaProfile
    first_question: str
    missing_slots: List[str]


class DynamicTurnRequest(BaseModel):
    history: List[str] = Field(default_factory=list)
    user_message: str
    hints: IntakeHints = Field(default_factory=IntakeHints)


class DynamicTurnResponse(BaseModel):
    persona: PersonaProfile
    ai_response: str
    missing_slots: List[str]
    done: bool = False
    summary: Optional[str] = None
    # Optional orchestration events (e.g., "Intake.A.ready")
    events: List[str] = Field(default_factory=list)
    # Captured Gate A values for the frontend and downstream agents
    captured: Dict[str, str] = Field(default_factory=dict)

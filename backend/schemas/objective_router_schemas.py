from __future__ import annotations

from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field


class ICPProfile(BaseModel):
    segment: str
    orientation: Optional[Literal["promotion", "prevention"]] = None


class ObjectiveRouterRequest(BaseModel):
    objective: str
    icp: ICPProfile
    business_type: Literal[
        "B2B SaaS PLG",
        "B2B SaaS SLG",
        "B2C ecommerce",
        "Marketplace",
        "Local services",
        "Content/Media",
        "Productivity tool",
        "Fintech",
    ]


class WOOP(BaseModel):
    wish: str
    outcome: str
    obstacle: str
    plan_if_then: str


class AlignOut(BaseModel):
    goal_statement: str
    woop: WOOP


class DiagnoseOut(BaseModel):
    comb_gaps: List[Literal["Capability", "Opportunity", "Motivation"]] = Field(default_factory=list)
    fogg_prompt: Literal["Spark", "Signal", "Facilitator"]


class ArchitectOut(BaseModel):
    north_star_inputs: List[str] = Field(default_factory=list)
    HEART: List[str] = Field(default_factory=list)


class PilotOut(BaseModel):
    barbell: Dict[str, List[str]] = Field(default_factory=dict)
    premortem_top_risks: List[str] = Field(default_factory=list)


class TrackTargets(BaseModel):
    baseline: float
    target: float
    p50: Optional[float] = None
    p80: Optional[float] = None


class TrackOut(BaseModel):
    targets: Dict[str, TrackTargets] = Field(default_factory=dict)
    forecast_eval: Literal["Brier"] = "Brier"
    cadence: str = "OODA two-week loop"


class ADAPTPlan(BaseModel):
    align: AlignOut
    diagnose: DiagnoseOut
    architect: ArchitectOut
    pilot: PilotOut
    track: TrackOut


class RouterClassifications(BaseModel):
    canonical_objective: Literal[
        "Awareness",
        "Acquisition",
        "Activation",
        "Revenue",
        "Retention",
        "Referral",
        "Efficiency",
        "Satisfaction",
    ]
    engagement_game: Literal["Attention", "Transaction", "Productivity"]
    north_star: str


class ObjectiveRouterResponse(BaseModel):
    objective_router_v1: Dict[str, Any]


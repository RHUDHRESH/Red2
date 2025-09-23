from __future__ import annotations

from typing import List, Literal, Optional, Dict, Any
from pydantic import BaseModel, Field, HttpUrl


class ADAPTAudience(BaseModel):
    segment: str = ""
    role: str = ""
    geo: str = ""
    awareness: Literal["problem", "solution", "product", "most"] = "problem"


class ADAPTOutcome(BaseModel):
    business: str = ""
    behavior: str = ""
    kpi: str = ""


class ProofAsset(BaseModel):
    type: Literal["stat", "quote", "case", "demo"]
    value: str
    source_url: Optional[HttpUrl] = None


class ADAPTTiming(BaseModel):
    urgency: Literal["low", "mid", "high"] = "mid"
    window: Literal["this_week", "this_month"] = "this_month"
    cadence: Literal["single", "drip"] = "single"


class ADAPT20(BaseModel):
    audience: ADAPTAudience
    desired_outcome: ADAPTOutcome
    advantages: List[str] = Field(default_factory=list)
    proof_assets: List[ProofAsset] = Field(default_factory=list)
    timing: ADAPTTiming
    risks: List[str] = Field(default_factory=list)


class FramePlan(BaseModel):
    primary: Literal[
        "authority",
        "social_proof",
        "scarcity",
        "reciprocity",
        "consistency",
        "liking",
        "unity",
    ]
    pre_suasion: str = ""
    guardrail: str = ""


class BehaviorBMAP(BaseModel):
    prompt: Literal["signal", "spark", "facilitator"]
    ability_lowering: Literal["default", "preset", "step_cut"] = "default"


class BehaviorCOMB(BaseModel):
    capability: str = ""
    opportunity: str = ""
    motivation: str = ""


class BehaviorEAST(BaseModel):
    easy: str = ""
    attractive: str = ""
    social: str = ""
    timely: str = ""


class BehaviorPlan(BaseModel):
    b_map: BehaviorBMAP
    com_b: BehaviorCOMB
    east: BehaviorEAST


class AssetDNA(BaseModel):
    claim: str
    evidence: List[ProofAsset] = Field(default_factory=list)
    warrant: str
    risks: List[str] = Field(default_factory=list)
    counters: List[str] = Field(default_factory=list)
    cta: Dict[str, str] = Field(default_factory=dict)


class MemeticRails(BaseModel):
    fluency_rules: List[str] = Field(default_factory=list)
    curiosity_seeds: List[str] = Field(default_factory=list)
    open_loops: List[str] = Field(default_factory=list)
    isolation_pop: str = ""
    peak_end: Dict[str, str] = Field(default_factory=dict)


class StyleMatch(BaseModel):
    lsm_score: int = 0
    notes: str = ""


class EarnedEffort(BaseModel):
    ikea_step: str = ""
    fallback: str = ""


class Pratfall(BaseModel):
    pratfall_note: str = ""


class CompileRequest(BaseModel):
    channel: Literal["email", "social", "landing"]
    adapt: ADAPT20
    frame: FramePlan
    behavior: BehaviorPlan
    dna: AssetDNA


class EmailDraft(BaseModel):
    subject: str
    line1: str
    body: str
    ps: Optional[str] = None


class SocialDraft(BaseModel):
    hook: str
    body: str
    close: str


class LandingOutline(BaseModel):
    hero: str
    proof_wall: List[str] = Field(default_factory=list)
    how_it_works: List[str] = Field(default_factory=list)
    cta_rail: str = ""


class Rubric(BaseModel):
    map_fit: int
    com_b_coverage: int
    east_compliance: int
    fluency_score: int
    lsm_score: int
    distinctiveness_index: int
    peak_end_delta: int
    prospect_alignment: int
    ikea_gain_risk: Literal["safe", "caution", "off"]
    pratfall_sanity: Literal["safe", "off"]
    red_flags: List[str] = Field(default_factory=list)


class CompileResponse(BaseModel):
    channel: str
    draft: Dict[str, Any]
    rails: MemeticRails
    style: StyleMatch
    earned_effort: EarnedEffort
    pratfall: Pratfall
    rubric: Rubric


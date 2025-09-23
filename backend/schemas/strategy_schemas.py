from __future__ import annotations

from typing import List, Optional, Literal, Dict
from pydantic import BaseModel, Field


# --- Unified State (subset) ---
class Tribe(BaseModel):
    name: str
    permission_level: Literal["cold", "warm", "hot"] = "cold"
    retell_line: str = ""


class SegmentOut(BaseModel):
    statement: str
    lead_count: int = 200
    leads_csv_base64: str


class WoundOut(BaseModel):
    per_month: float
    currency: str = "INR"
    triggers: List[str] = Field(default_factory=list)
    citations: List[str] = Field(default_factory=list)


class ReframeOut(BaseModel):
    category: str
    enemy: str
    claims: List[str] = Field(default_factory=list)
    proof: List[str] = Field(default_factory=list)
    do_not_say: List[str] = Field(default_factory=list)
    focus_word: str = ""


class OfferOut(BaseModel):
    outcome: str
    deliverables: List[str] = Field(default_factory=list)
    guarantee: str


class OutreachMsg(BaseModel):
    prospect: str = ""
    opener: str
    cta: str


class ActionOut(BaseModel):
    messages: List[OutreachMsg] = Field(default_factory=list)


class CashOut(BaseModel):
    pilot_scope: str = "7 days"
    upi_qr: str = ""
    deposit_amount: float = 0.0


class GovernanceOut(BaseModel):
    cac_cap: float = 200.0
    roas_kill_days: int = 14
    churn_cap_pct: float = 20.0


class Play(BaseModel):
    type: Literal["lateral", "vertical"]
    shift_axis: Optional[Literal["target", "occasion", "need", "element"]] = None
    hook: str
    channels: List[str] = Field(default_factory=list)
    aisas: Dict[str, Dict] = Field(default_factory=dict)
    unit_econ: Dict[str, float] = Field(default_factory=dict)
    risk: Dict[str, List[str]] = Field(default_factory=dict)


# --- Requests ---
class SegmentRequest(BaseModel):
    seed_keyword: str
    competitor: str
    region: str


class WoundRequest(BaseModel):
    leads_csv_base64: str


class ReframeRequest(BaseModel):
    competitor_set: List[str] = Field(default_factory=list)


class OfferRequest(BaseModel):
    wound: WoundOut


class ActionRequest(BaseModel):
    offer: OfferOut
    leads_csv_base64: str


class CashRequest(BaseModel):
    accepted_replies: List[str] = Field(default_factory=list)


class CashGuardRequest(BaseModel):
    bank_balance_inr: float
    receivables_inr: float
    payables_inr: float
    ad_spend_last_7_inr: float


class CashGuardResponse(BaseModel):
    throttle_plan: List[str] = Field(default_factory=list)


class PermissionRequest(BaseModel):
    story_assets: List[str] = Field(default_factory=list)


class PermissionResponse(BaseModel):
    opt_in_rate: float
    retell_rate_10w: float
    notes: str = ""


class LateralVerticalRequest(BaseModel):
    product: str
    segment: str
    usage_data: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)


class LateralVerticalResponse(BaseModel):
    lateral: List[Play]
    vertical: List[Play]


class AISASRequest(BaseModel):
    approved_play: Play


class AISASResponse(BaseModel):
    pack: Dict[str, Dict]


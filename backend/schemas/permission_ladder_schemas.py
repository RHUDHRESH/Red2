from __future__ import annotations

from typing import List, Literal
from pydantic import BaseModel, Field, HttpUrl


class ReciprocityOffer(BaseModel):
    title: str
    asset_url: HttpUrl


class MicroAsk(BaseModel):
    label: str
    time_to_do: str
    success_criteria: str


class PromptSpec(BaseModel):
    rung: Literal["R1", "R2", "R3", "R4", "R5", "R6"]
    type: Literal["Facilitator", "Signal", "Spark"]
    copy: str
    trigger_timing: str


class OptInStep(BaseModel):
    send_at: str
    subject: str
    body_outline: str
    legal_block: str


class CommunityEntry(BaseModel):
    channel: Literal["Discord", "WhatsApp", "Telegram", "Slack"]
    purpose: str
    capacity_cap: int = 150


class GrowthLoop(BaseModel):
    name: Literal["content_loop", "invite_loop", "product_loop"]
    input: str
    process: str
    output: str
    reinvestment: str


class PermissionLadderBlueprint(BaseModel):
    audience_identity: List[dict] = Field(default_factory=list)
    reciprocity_offers: List[ReciprocityOffer] = Field(default_factory=list)
    micro_asks: List[MicroAsk] = Field(default_factory=list)
    prompts: List[PromptSpec] = Field(default_factory=list)
    opt_in_sequence: List[OptInStep] = Field(default_factory=list)
    community_entry_points: List[CommunityEntry] = Field(default_factory=list)
    cadence_rules: dict = Field(default_factory=dict)
    growth_loops: List[GrowthLoop] = Field(default_factory=list)
    kpis: dict = Field(default_factory=dict)
    compliance: dict = Field(default_factory=dict)


class PermissionLadderRequest(BaseModel):
    story_assets: List[str] = Field(default_factory=list)
    lead_magnet_angle: str = ""


class PermissionLadderResponse(BaseModel):
    blueprint: PermissionLadderBlueprint


from __future__ import annotations

from typing import List, Dict
from pydantic import BaseModel, Field


class CompetitorSnapshot(BaseModel):
    name: str
    position: str = ""
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)


class BrandVoice(BaseModel):
    personality: List[str] = Field(default_factory=list)
    tone_notes: List[str] = Field(default_factory=list)
    rhythm: str = ""
    vocabulary_do: List[str] = Field(default_factory=list)
    vocabulary_dont: List[str] = Field(default_factory=list)


class MeasurementTier(BaseModel):
    metrics: Dict[str, str] = Field(default_factory=dict)


class FounderBrandInput(BaseModel):
    founder_name: str
    desired_word: str
    target_audience: str
    differentiators: List[str] = Field(default_factory=list)
    competitors: List[CompetitorSnapshot] = Field(default_factory=list)


class FounderBrandCodex(BaseModel):
    positioning_core: Dict[str, str] = Field(default_factory=dict)
    narrative_buckets: Dict[str, List[str]] = Field(default_factory=dict)
    audience_resonance_map: Dict[str, str] = Field(default_factory=dict)
    voice: BrandVoice
    content_mapping: Dict[str, List[str]] = Field(default_factory=dict)
    asymmetric_moves: List[str] = Field(default_factory=list)
    measurement: Dict[str, MeasurementTier] = Field(default_factory=dict)


class FounderBrandResponse(BaseModel):
    codex: FounderBrandCodex


from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class SourceRef(BaseModel):
    title: str
    url: str
    source: str


class ICEScore(BaseModel):
    impact: float = 5.0
    confidence: float = 5.0
    ease: float = 5.0

    @property
    def score(self) -> float:
        return round(self.impact * self.confidence * self.ease, 2)


class MicroPlay(BaseModel):
    id: str
    channel: str  # FOH | delivery | UGC
    title: str
    description: str
    rationale: str
    sources: List[SourceRef] = Field(default_factory=list)
    ice: ICEScore
    kpis: List[str] = Field(default_factory=list)
    ab_variant_codes: List[str] = Field(default_factory=list)
    sop_pdf_base64: Optional[str] = None


class MicroPlayRequest(BaseModel):
    restaurant_name: str
    city: Optional[str] = None
    cuisine: Optional[str] = None
    baseline_ok: Optional[bool] = True
    avg_rating: Optional[float] = None
    notes: Optional[str] = None
    max_items: int = 6


class MicroPlayResponse(BaseModel):
    suppressed: bool = False
    reason: Optional[str] = None
    plays: List[MicroPlay] = Field(default_factory=list)
    kpis: List[str] = Field(default_factory=list)


class ChecklistItem(BaseModel):
    id: str
    text: str
    rationale: Optional[str] = None
    refs: List[SourceRef] = Field(default_factory=list)


class VibeCheckRequest(BaseModel):
    brand: str
    notes: Optional[str] = None


class VibeCheckResponse(BaseModel):
    checklists: List[ChecklistItem] = Field(default_factory=list)
    nudges: List[str] = Field(default_factory=list)
    kpis: List[str] = Field(default_factory=list)


from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl


class CompetitorScanRequest(BaseModel):
    query: str = Field(..., description="Market or topic to scan, e.g., 'cloud kitchen Chennai' or 'biryani delivery' ")
    max_candidates: int = Field(12, ge=3, le=40)
    per_source: int = Field(6, ge=1, le=20)


class CompetitorSignal(BaseModel):
    platform: str
    title: str = ""
    url: HttpUrl
    snippet: str = ""


class CompetitorCard(BaseModel):
    name: str
    homepage: Optional[HttpUrl] = None
    description: str = ""
    keywords: List[str] = Field(default_factory=list)
    signals: List[CompetitorSignal] = Field(default_factory=list)
    strength_score: float = 0.0
    positioning: str = ""


class CompetitorScanResponse(BaseModel):
    topic: str
    competitors: List[CompetitorCard]
    notes: str = ""


from __future__ import annotations

from typing import List, Optional, Literal
from pydantic import BaseModel, Field, HttpUrl


Stance = Literal["support", "contradict", "unclear"]


class CopyAuditRequest(BaseModel):
    copy_text: str = Field(..., description="Marketing copy whose claims should be linked to evidence")
    seed_urls: List[HttpUrl] = Field(default_factory=list, description="Optional known trustworthy sources to search within")
    max_claims: int = Field(15, ge=1, le=50)
    evidence_per_claim: int = Field(6, ge=1, le=15)
    language: str = Field("en")


class EvidenceItem(BaseModel):
    url: HttpUrl
    title: str = ""
    summary: str = ""
    source_type: Literal["web", "news", "wiki"] = "web"
    stance: Stance = "unclear"
    confidence: float = 0.0


class ClaimItem(BaseModel):
    text: str
    severity: Literal["low", "medium", "high"] = "medium"


class ClaimEvidence(BaseModel):
    claim: ClaimItem
    evidence: List[EvidenceItem] = Field(default_factory=list)
    suggestions: List["RewriteOption"] = Field(default_factory=list)


class CopyAuditResponse(BaseModel):
    total_claims: int
    supported_claims: int
    contradictory_claims: int
    unsupported_claims: int
    claims: List[ClaimEvidence]
    notes: str = ""


class RewriteOption(BaseModel):
    text_with_citations: str = Field(..., description="Safer phrasing with inline citations like [1], [2]")
    rationale: str = ""


class ApplyChange(BaseModel):
    old: str
    new: str


class RewriteApplyRequest(BaseModel):
    copy_text: str
    changes: List[ApplyChange]


class RewriteApplyResponse(BaseModel):
    revised_text: str

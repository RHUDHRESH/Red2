from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl


class LandingPageRequest(BaseModel):
    product_summary: str = Field(..., description="1-3 sentences describing the offer")
    value_props: List[str] = Field(default_factory=list, description="Key value props (bullets)")
    target_audience: str = Field("", description="Who this is for")
    tone: str = Field("friendly", description="Writing tone (e.g., friendly, professional)")
    language: str = Field("en", description="Output language code")
    references: List[HttpUrl] = Field(default_factory=list, description="Optional URLs to inform copy")


class HeroSection(BaseModel):
    headline: str
    subheadline: str
    primary_cta: str
    secondary_cta: Optional[str] = None


class PageSection(BaseModel):
    heading: str
    body: str
    bullets: List[str] = Field(default_factory=list)


class FAQItem(BaseModel):
    question: str
    answer: str


class LandingPageBlueprint(BaseModel):
    meta_title: str
    meta_description: str
    hero: HeroSection
    sections: List[PageSection] = Field(default_factory=list)
    social_proof: List[str] = Field(default_factory=list)
    faqs: List[FAQItem] = Field(default_factory=list)
    utm_campaign: str = ""
    compliance_notes: str = ""


class LandingPageResponse(BaseModel):
    language: str
    blueprint: LandingPageBlueprint
    used_references: List[HttpUrl] = Field(default_factory=list)


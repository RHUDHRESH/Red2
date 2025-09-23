from __future__ import annotations

from typing import List, Optional, Tuple
from pydantic import BaseModel, Field, HttpUrl


class PartnerOutreachRequest(BaseModel):
    latitude: float
    longitude: float
    radius_m: int = Field(3000, ge=200, le=20000)
    partner_types: List[str] = Field(default_factory=lambda: ["gym", "university", "coworking", "office"])
    business_summary: str = Field(..., description="1-3 sentences about your business and offer")
    language: str = Field("en", description="Language for outreach copy")
    max_partners: int = Field(16, ge=4, le=40)


class PartnerCandidate(BaseModel):
    name: str
    location: Tuple[float, float]
    types: List[str] = Field(default_factory=list)
    user_ratings_total: int = 0
    distance_m: int = 0
    travel_time_min: int = 0


class EnrichedPartner(BaseModel):
    name: str
    address: Optional[str] = None
    website: Optional[HttpUrl] = None
    linkedin_url: Optional[HttpUrl] = None
    email: Optional[str] = None
    distance_m: int = 0
    travel_time_min: int = 0
    notes: str = ""


class OutreachTemplate(BaseModel):
    subject: str
    email_body: str
    dm_message: str


class PartnerOutreachCard(BaseModel):
    partner: EnrichedPartner
    outreach: OutreachTemplate


class PartnerOutreachResponse(BaseModel):
    area_center: Tuple[float, float]
    partners: List[PartnerOutreachCard]


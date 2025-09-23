from __future__ import annotations

from typing import List, Optional, Literal, Tuple
from pydantic import BaseModel, Field, HttpUrl


# --- Cohort Trait Schema (rich but optional) ---
class Demographic(BaseModel):
    age: Optional[str] = None  # e.g., "25-34"
    gender: Optional[str] = None
    marital_status: Optional[str] = None
    education: Optional[str] = None
    occupation: Optional[str] = None
    household_role: Optional[str] = None
    household_structure: Optional[str] = None
    location: Optional[str] = None  # region/city/urban-rural


class Economic(BaseModel):
    personal_income: Optional[str] = None
    household_income_access: Optional[str] = None
    spending_control: Optional[str] = None
    financial_attitude: Optional[str] = None
    payment_preferences: List[str] = Field(default_factory=list)


class Psychographic(BaseModel):
    values: List[str] = Field(default_factory=list)
    aspirations: List[str] = Field(default_factory=list)
    pain_points: List[str] = Field(default_factory=list)
    personality: Optional[str] = None


class SocialCultural(BaseModel):
    religion_culture: Optional[str] = None
    languages: List[str] = Field(default_factory=list)
    peer_influence: Optional[str] = None
    status_cues: Optional[str] = None


class Behavioral(BaseModel):
    digital_access: Optional[str] = None
    media_consumption: List[str] = Field(default_factory=list)
    shopping_channels: List[str] = Field(default_factory=list)
    purchase_frequency: Optional[str] = None
    offer_response: List[str] = Field(default_factory=list)  # discount, cashback, bundle, referral, festival
    decision_maker_for: List[str] = Field(default_factory=list)


class Trust(BaseModel):
    trusted_sources: List[str] = Field(default_factory=list)
    brand_affinities: List[str] = Field(default_factory=list)


class SourceRef(BaseModel):
    url: HttpUrl
    title: str = ""
    summary: str = ""


class CohortSpec(BaseModel):
    name: str
    tags: List[str] = Field(default_factory=list)
    demographic: Demographic = Field(default_factory=Demographic)
    economic: Economic = Field(default_factory=Economic)
    psychographic: Psychographic = Field(default_factory=Psychographic)
    social_cultural: SocialCultural = Field(default_factory=SocialCultural)
    behavioral: Behavioral = Field(default_factory=Behavioral)
    trust: Trust = Field(default_factory=Trust)
    target_size: int = Field(100, ge=10, le=5000)


# --- Synthetic Individual Row ---
class SyntheticPerson(BaseModel):
    cohort: str
    age: Optional[int] = None
    gender: Optional[str] = None
    marital_status: Optional[str] = None
    education: Optional[str] = None
    occupation: Optional[str] = None
    household_role: Optional[str] = None
    household_structure: Optional[str] = None
    location: Optional[str] = None

    personal_income: Optional[str] = None
    spending_control: Optional[str] = None
    payment_method: Optional[str] = None

    values: List[str] = Field(default_factory=list)
    aspirations: List[str] = Field(default_factory=list)
    pain_points: List[str] = Field(default_factory=list)

    religion_culture: Optional[str] = None
    languages: List[str] = Field(default_factory=list)

    digital_access: Optional[str] = None
    media_primary: Optional[str] = None
    shopping_channel: Optional[str] = None
    purchase_pattern: Optional[str] = None
    offer_response: Optional[str] = None
    decision_maker_for: List[str] = Field(default_factory=list)

    trusted_source: Optional[str] = None
    brand_affinity: Optional[str] = None


class CohortDataset(BaseModel):
    cohort: str
    rules_used: List[str] = Field(default_factory=list)
    sources: List[SourceRef] = Field(default_factory=list)
    people: List[SyntheticPerson] = Field(default_factory=list)
    survey_csv_base64: Optional[str] = None


class SyntheticGenRequest(BaseModel):
    cohorts: List[CohortSpec]
    include_pattern_mining: bool = True
    use_sdv: bool = False
    language: str = "en"


class SyntheticGenResponse(BaseModel):
    cohorts: List[CohortDataset]
    notes: str = ""

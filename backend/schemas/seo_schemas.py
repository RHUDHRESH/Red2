from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl


class SEOSourceNote(BaseModel):
    url: HttpUrl
    title: str = ""
    summary: str = ""
    keywords: List[str] = Field(default_factory=list)


class SEOBriefRequest(BaseModel):
    topic: str = Field(..., description="Primary topic or keyword intent")
    seed_urls: List[HttpUrl] = Field(default_factory=list)
    max_sources: int = Field(8, ge=3, le=20)
    language: str = Field("en", description="Output language (e.g., 'en', 'hi')")


class OutlineSection(BaseModel):
    heading: str
    hints: List[str] = Field(default_factory=list)


class SEOBrief(BaseModel):
    meta_title: str
    meta_description: str
    primary_keyword: str
    secondary_keywords: List[str] = Field(default_factory=list)
    outline: List[OutlineSection] = Field(default_factory=list)
    faqs: List[str] = Field(default_factory=list)
    references: List[HttpUrl] = Field(default_factory=list)


class SEOBriefResponse(BaseModel):
    topic: str
    language: str
    sources: List[SEOSourceNote]
    brief: SEOBrief


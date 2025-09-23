from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl


class ResearchRequest(BaseModel):
    query: str = Field(..., description="Primary research question or topic")
    max_results: int = Field(8, ge=1, le=25, description="Max search results to consider")
    max_pages: int = Field(6, ge=1, le=20, description="Max pages to fetch and analyze")
    include_domains: List[str] = Field(default_factory=list, description="Only include results from these domains (optional)")
    exclude_domains: List[str] = Field(default_factory=list, description="Exclude results from these domains (optional)")
    language: str = Field("en", description="Preferred language for results")


class SourceNote(BaseModel):
    url: HttpUrl
    title: str = ""
    key_points: List[str] = Field(default_factory=list)
    summary: str = ""


class ResearchFinding(BaseModel):
    statement: str
    confidence: float = Field(ge=0.0, le=1.0, default=0.6)
    citations: List[HttpUrl] = Field(default_factory=list)


class ResearchResponse(BaseModel):
    query: str
    findings: List[ResearchFinding]
    sources: List[SourceNote]


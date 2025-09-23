from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class SocialCalendarRequest(BaseModel):
    topic: str = Field(..., description="Primary topic or campaign theme")
    platforms: List[str] = Field(default_factory=lambda: ["instagram", "twitter", "linkedin"])
    weeks: int = Field(4, ge=1, le=8)
    posts_per_week: int = Field(5, ge=1, le=14)
    start_date: Optional[str] = Field(None, description="YYYY-MM-DD; if omitted, use today")
    language: str = Field("en")


class SocialPostPlan(BaseModel):
    platform: str
    date: str
    theme: str
    idea: str
    caption: str
    hashtags: List[str] = Field(default_factory=list)


class SocialCalendarResponse(BaseModel):
    topic: str
    start_date: str
    weeks: int
    posts: List[SocialPostPlan]
    notes: str = ""


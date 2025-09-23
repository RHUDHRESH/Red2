from __future__ import annotations

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class Asset(BaseModel):
    id: str
    kind: str = Field(description="e.g., doc, sheet, image, video, pdf")
    title: Optional[str] = None
    content: Optional[str] = None
    url: Optional[str] = None
    source: str = Field(description="connector name, e.g., google_docs, notion")
    created_at: Optional[int] = None
    updated_at: Optional[int] = None
    extra: Dict = Field(default_factory=dict)


class Post(BaseModel):
    id: str
    channel: str = Field(description="e.g., twitter, discord, youtube")
    text: str
    media_urls: List[str] = Field(default_factory=list)
    scheduled_at: Optional[int] = None
    source: str = Field(default="")
    external_id: Optional[str] = None
    extra: Dict = Field(default_factory=dict)


class Comment(BaseModel):
    id: str
    post_id: str
    author: str
    text: str
    created_at: Optional[int] = None
    source: str = Field(default="")
    external_id: Optional[str] = None
    extra: Dict = Field(default_factory=dict)


class Event(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    start_ts: int
    end_ts: int
    location: Optional[str] = None
    source: str = Field(default="")
    external_id: Optional[str] = None  # e.g., Google event id
    extra: Dict = Field(default_factory=dict)


class Metric(BaseModel):
    name: str
    value: float
    unit: str = ""
    dims: Dict[str, str] = Field(default_factory=dict)
    ts: Optional[int] = None


from __future__ import annotations

from typing import List, Optional, Literal, Dict
from pydantic import BaseModel, Field, EmailStr


class Attachment(BaseModel):
    name: str
    mime: str
    base64: str


class ActionLog(BaseModel):
    type: str
    status: Literal["ok", "error", "skipped"] = "ok"
    details: str = ""


class ChatTurnRequest(BaseModel):
    user_message: str
    email_to: Optional[EmailStr] = None
    location_query: Optional[str] = None
    start_datetime_iso: Optional[str] = None
    end_datetime_iso: Optional[str] = None
    preferences: Dict[str, str] = Field(default_factory=dict)
    forced_tools: List[str] = Field(default_factory=list, description="Force-run specific tools like 'research', 'social_calendar', 'offer_assets'")


class ChatTurnResponse(BaseModel):
    assistant_message: str
    clarifying_questions: List[str] = Field(default_factory=list)
    actions: List[ActionLog] = Field(default_factory=list)
    attachments: List[Attachment] = Field(default_factory=list)

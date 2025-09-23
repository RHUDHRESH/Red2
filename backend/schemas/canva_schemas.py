from __future__ import annotations

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class CanvaDesignRequest(BaseModel):
    description: str
    format_hint: str = Field(
        default="instagram_post",
        description="High-level format e.g., instagram_post, story, poster, flyer, presentation_slide",
    )
    variants: int = Field(default=1, ge=1, le=20)


class CanvaDesignResponse(BaseModel):
    template_link: Optional[str] = None
    design_brief: Dict
    bulk_create_csv_base64: Optional[str] = None
    notes: str = ""


from pydantic import BaseModel, Field
from typing import List, Dict
from .move_schemas import AssetBrief

class CreativeAsset(BaseModel):
    """
    Represents a single, generated creative asset, ready for production.
    """
    id: str = Field(..., description="Unique ID for the final asset, e.g., asset_final_123.")
    asset_brief_id: str = Field(..., description="The ID of the brief this asset fulfills.")
    channel: str = Field(..., description="The channel this asset is for, e.g., 'instagram_reels'.")
    headline: str | None = Field(default=None, description="The primary headline or hook for the ad/post.")
    body_copy: str = Field(..., description="The main text content of the asset.")
    visual_suggestion: str = Field(..., description="A concrete suggestion for the visual element, e.g., 'A fast-paced video showing hands packing a tiffin box in under 10 seconds.'")

class AssetPackage(BaseModel):
    """
    The final output of the Creative Director Agent. This is a collection of all
    the generated creative assets for a given Strike Plan.
    """
    strike_plan_id: str
    assets: List[CreativeAsset]

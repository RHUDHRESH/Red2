from __future__ import annotations

from fastapi import APIRouter, HTTPException

from agents.restaurant_micro_strategy_agent import run_restaurant_micro_strategy
from agents.platform_ops_copilot_agent import run_platform_vibe_check
from schemas.ops_schemas import (
    MicroPlayRequest,
    MicroPlayResponse,
    VibeCheckRequest,
    VibeCheckResponse,
)


router = APIRouter()


@router.post("/restaurant/microplays", response_model=MicroPlayResponse)
async def restaurant_microplays(req: MicroPlayRequest):
    try:
        return await run_restaurant_micro_strategy(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/platform/vibe-check", response_model=VibeCheckResponse)
async def platform_vibe_check(req: VibeCheckRequest):
    try:
        return await run_platform_vibe_check(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


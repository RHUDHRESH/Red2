from fastapi import APIRouter, HTTPException

from agents.strategy_engine import (
    run_segment, run_wound, run_reframe, run_offer, run_action, run_cash,
    run_cashguard, run_permission, run_lateral_vertical, run_aisas,
)
from schemas.strategy_schemas import (
    SegmentRequest, SegmentOut,
    WoundRequest, WoundOut,
    ReframeRequest, ReframeOut,
    OfferRequest, OfferOut,
    ActionRequest, ActionOut,
    CashRequest, CashOut,
    CashGuardRequest, CashGuardResponse,
    PermissionRequest, PermissionResponse,
    LateralVerticalRequest, LateralVerticalResponse,
    AISASRequest, AISASResponse,
)


router = APIRouter()


@router.post("/run/segment", response_model=SegmentOut)
async def run_segment_ep(req: SegmentRequest):
    try:
        return await run_segment(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run/wound", response_model=WoundOut)
async def run_wound_ep(req: WoundRequest):
    try:
        return await run_wound(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run/reframe", response_model=ReframeOut)
async def run_reframe_ep(req: ReframeRequest):
    try:
        return await run_reframe(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run/offer", response_model=OfferOut)
async def run_offer_ep(req: OfferRequest):
    try:
        return await run_offer(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run/action", response_model=ActionOut)
async def run_action_ep(req: ActionRequest):
    try:
        return await run_action(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run/cash", response_model=CashOut)
async def run_cash_ep(req: CashRequest):
    try:
        return await run_cash(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/govern/cashguard/check", response_model=CashGuardResponse)
async def cashguard_ep(req: CashGuardRequest):
    try:
        return await run_cashguard(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tribe/permission", response_model=PermissionResponse)
async def permission_ep(req: PermissionRequest):
    try:
        return await run_permission(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/play/lateral-vertical", response_model=LateralVerticalResponse)
async def lateral_vertical_ep(req: LateralVerticalRequest):
    try:
        return await run_lateral_vertical(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/aisas/router", response_model=AISASResponse)
async def aisas_ep(req: AISASRequest):
    try:
        return await run_aisas(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


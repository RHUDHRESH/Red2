from fastapi import APIRouter, HTTPException

from agents.neurofoundry_agent import (
    normalize_adapt,
    select_frame,
    map_behavior,
    build_dna,
    compile_asset,
)
from schemas.neurofoundry_schemas import (
    ADAPT20,
    FramePlan,
    BehaviorPlan,
    AssetDNA,
    CompileRequest,
    CompileResponse,
)


router = APIRouter()


@router.post("/adapt/normalize", response_model=ADAPT20)
async def adapt_normalize_ep(body: dict):
    try:
        return normalize_adapt(body)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/frame/select", response_model=FramePlan)
async def frame_select_ep(adapt: ADAPT20):
    try:
        return select_frame(adapt)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/behavior/map", response_model=BehaviorPlan)
async def behavior_map_ep(adapt: ADAPT20):
    try:
        return map_behavior(adapt)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dna/build", response_model=AssetDNA)
async def dna_build_ep(adapt: ADAPT20):
    try:
        return build_dna(adapt)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compile", response_model=CompileResponse)
async def compile_ep(req: CompileRequest):
    try:
        return compile_asset(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


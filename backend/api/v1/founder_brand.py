from fastapi import APIRouter, HTTPException

from agents.founder_brand_agent import generate_codex
from schemas.founder_brand_schemas import FounderBrandInput, FounderBrandResponse


router = APIRouter()


@router.post("/codex", response_model=FounderBrandResponse)
async def codex_ep(req: FounderBrandInput):
    try:
        return generate_codex(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


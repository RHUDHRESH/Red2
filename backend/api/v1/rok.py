from fastapi import APIRouter, HTTPException

from agents.rok_knife_agent import generate_big_idea
from schemas.rok_schemas import ROKInput, ROKOutput


router = APIRouter()


@router.post("/generate", response_model=ROKOutput)
async def generate_ep(req: ROKInput):
    try:
        return generate_big_idea(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


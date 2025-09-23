from fastapi import APIRouter, HTTPException

from agents.synthetic_behavior_agent import run_synthetic_generation
from schemas.synthetic_schemas import SyntheticGenRequest, SyntheticGenResponse


router = APIRouter()


@router.post("/generate", response_model=SyntheticGenResponse)
async def generate_synthetic(req: SyntheticGenRequest):
    try:
        result = await run_synthetic_generation(req.model_dump())
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected synthetic generation error: {e}")


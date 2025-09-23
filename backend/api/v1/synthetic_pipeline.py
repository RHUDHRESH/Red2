from fastapi import APIRouter, HTTPException

from agents.synthetic_pipeline_agent import run_synthetic_icp_pipeline
from schemas.synthetic_schemas import SyntheticGenRequest


router = APIRouter()


@router.post("/run")
async def run_pipeline(req: SyntheticGenRequest):
    try:
        result = await run_synthetic_icp_pipeline(req.model_dump())
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected pipeline error: {e}")


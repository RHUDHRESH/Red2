from fastapi import APIRouter, HTTPException

from agents.competitor_intel_agent import run_competitor_scan
from schemas.competitor_schemas import CompetitorScanRequest, CompetitorScanResponse


router = APIRouter()


@router.post("/scan", response_model=CompetitorScanResponse)
async def scan_competitors(req: CompetitorScanRequest):
    try:
        result = await run_competitor_scan(req.model_dump())
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error during competitor scan: {e}")


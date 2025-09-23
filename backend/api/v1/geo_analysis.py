
from fastapi import APIRouter, HTTPException
from agents.market_analysis_agent import run_market_analysis_agent
from schemas.geo_schemas import LocationRequest
router = APIRouter()
@router.post("/analyze-location")
async def analyze_location(request: LocationRequest):
    try:
        result = await run_market_analysis_agent(request.model_dump())
        if "error" in result: raise HTTPException(status_code=500, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

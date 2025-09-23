from fastapi import APIRouter, HTTPException

from agents.landing_page_agent import run_landing_page
from schemas.landing_schemas import LandingPageRequest, LandingPageResponse


router = APIRouter()


@router.post("/generate", response_model=LandingPageResponse)
async def generate_landing(req: LandingPageRequest):
    try:
        result = await run_landing_page(req.model_dump())
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected landing generator error: {e}")


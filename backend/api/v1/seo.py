from fastapi import APIRouter, HTTPException

from agents.seo_brief_agent import run_seo_brief
from schemas.seo_schemas import SEOBriefRequest, SEOBriefResponse


router = APIRouter()


@router.post("/brief", response_model=SEOBriefResponse)
async def generate_seo_brief(req: SEOBriefRequest):
    try:
        result = await run_seo_brief(req.model_dump())
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected SEO brief error: {e}")


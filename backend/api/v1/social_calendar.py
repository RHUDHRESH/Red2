from fastapi import APIRouter, HTTPException

from agents.social_calendar_agent import run_social_calendar
from schemas.social_calendar_schemas import SocialCalendarRequest, SocialCalendarResponse


router = APIRouter()


@router.post("/build", response_model=SocialCalendarResponse)
async def build_calendar(req: SocialCalendarRequest):
    try:
        result = await run_social_calendar(req.model_dump())
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected social calendar error: {e}")


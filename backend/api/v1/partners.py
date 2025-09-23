from fastapi import APIRouter, HTTPException

from agents.partner_outreach_agent import run_partner_outreach
from schemas.partner_schemas import PartnerOutreachRequest, PartnerOutreachResponse


router = APIRouter()


@router.post("/outreach", response_model=PartnerOutreachResponse)
async def build_outreach(req: PartnerOutreachRequest):
    try:
        result = await run_partner_outreach(req.model_dump())
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected outreach error: {e}")



from fastapi import APIRouter, HTTPException
import logging
from agents.positioning_agent import run_positioning_agent
from schemas.positioning_schemas import PositioningGenerationRequest, PositioningResponse

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/generate-options", response_model=PositioningResponse)
async def generate_options(request: PositioningGenerationRequest):
    """
    Receives facts and claims from an intake interview and triggers the
    Positioning Agent to generate and validate strategic options.
    """
    try:
        result = await run_positioning_agent(request.model_dump())
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except Exception as e:
        logger.exception("Unexpected error in positioning agent")
        raise HTTPException(status_code=500, detail="An internal error occurred while generating positioning options.")

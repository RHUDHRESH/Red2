from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from schemas.positioning_schemas import PositioningOptionCard
from agents.objection_agent import run_objection_agent
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class ObjectionRequest(BaseModel):
    option_card: PositioningOptionCard
    objection_text: str

@router.post("/handle")
async def handle_objection(request: ObjectionRequest):
    """
    Receives a positioning card and a user's objection,
    then invokes the objection agent to process and revise it.
    """
    try:
        logger.info(f"Received objection for card: {request.option_card.one_word}")
        result = await run_objection_agent(request.model_dump())
        
        if result.get("status") == "failed":
            # The agent handled the error and returned a friendly message
            raise HTTPException(status_code=400, detail=result.get("message", "Agent failed to process the objection."))
            
        return result
    except Exception as e:
        logger.error(f"Unhandled error in objection API: {e}", exc_info=True)
        # This catches errors outside the agent's handled exceptions
        raise HTTPException(status_code=500, detail="A critical internal error occurred.")

from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field
from typing import Dict, Any

from agents.outcome_agent import run_outcome_committer_agent
from schemas.cohort_schemas import EnrichedCohort

router = APIRouter()

class OutcomeRequest(BaseModel):
    high_level_goal: str = Field(..., example="Increase lunch orders from students.")
    target_cohort: EnrichedCohort

@router.post("/draft-charter")
async def draft_charter(request: OutcomeRequest):
    """
    Receives a high-level goal and a target cohort, then runs the
    Outcome Committer Agent to generate a draft charter.
    """
    try:
        result = await run_outcome_committer_agent(
            high_level_goal=request.high_level_goal,
            target_cohort_dict=request.target_cohort.model_dump()
        )
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from schemas.outcome_schemas import OutcomeCharter
from schemas.cohort_schemas import EnrichedCohort
from agents.move_maker_agent import run_move_maker_agent

router = APIRouter()

class MoveMakerRequest(BaseModel):
    outcome_charter: OutcomeCharter
    target_cohort: EnrichedCohort

@router.post("/generate-plan")
async def generate_strike_plan(request: MoveMakerRequest):
    """
    Receives an Outcome Charter and a target Cohort, then invokes the
    Move Maker agent to generate a detailed Strike Plan.
    """
    try:
        result = await run_move_maker_agent(
            outcome_charter_dict=request.outcome_charter.model_dump(),
            target_cohort_dict=request.target_cohort.model_dump()
        )
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except Exception as e:
        # Catch any unexpected errors during the process
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


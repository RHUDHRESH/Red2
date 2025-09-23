from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agents.creative_agent import run_creative_director_agent
from schemas.move_schemas import StrikePlan
from schemas.outcome_schemas import OutcomeCharter

router = APIRouter()


class CreativeRequest(BaseModel):
    strike_plan: StrikePlan
    outcome_charter: OutcomeCharter


@router.post("/generate-assets")
async def generate_creative_assets(request: CreativeRequest):
    """
    Receives a Strike Plan and its corresponding Outcome Charter,
    then invokes the Creative Director agent to generate all the necessary assets.
    """
    try:
        result = await run_creative_director_agent(
            strike_plan_dict=request.strike_plan.model_dump(),
            outcome_charter_dict=request.outcome_charter.model_dump()
        )
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except Exception as e:
        # Catch any unexpected errors during the process
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

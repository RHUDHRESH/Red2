from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agents.archive_agent import run_archive_agent, run_recommendation_agent
from schemas.outcome_schemas import OutcomeCharter
from schemas.move_schemas import StrikePlan
from schemas.attribution_schemas import AttributionReport

router = APIRouter()

class ArchiveRequest(BaseModel):
    strike_plan: StrikePlan
    outcome_charter: OutcomeCharter
    attribution_report: AttributionReport

class RecommendRequest(BaseModel):
    new_goal: str

@router.post("/archive-playbook")
async def archive_playbook(request: ArchiveRequest):
    """
    Receives a completed campaign's data and invokes the archive agent
    to save it as a reusable playbook.
    """
    try:
        result = await run_archive_agent(
            strike_plan=request.strike_plan.model_dump(),
            charter=request.outcome_charter.model_dump(),
            report=request.attribution_report.model_dump()
        )
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

@router.post("/recommend-next-move")
async def recommend_next_move(request: RecommendRequest):
    """
    Receives a new marketing goal and asks the agent to recommend the
    most relevant playbook from the archive.
    """
    try:
        result = await run_recommendation_agent(new_goal=request.new_goal)
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

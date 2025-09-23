from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from schemas.move_schemas import StrikePlan
from schemas.creative_schemas import AssetPackage
from agents.scheduler_agent import run_scheduler_agent

router = APIRouter()

class SchedulerRequest(BaseModel):
    strike_plan: StrikePlan
    asset_package: AssetPackage

@router.post("/build-schedule")
async def build_schedule(request: SchedulerRequest):
    """
    Receives a Strike Plan and an Asset Package, then invokes the
    Scheduler agent to generate a final, executable schedule of jobs.
    """
    try:
        result = await run_scheduler_agent(
            strike_plan_dict=request.strike_plan.model_dump(),
            asset_package_dict=request.asset_package.model_dump()
        )
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except Exception as e:
        # Catch any unexpected errors during the process
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

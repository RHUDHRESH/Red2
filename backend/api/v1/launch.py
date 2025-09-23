from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from schemas.scheduler_schemas import SchedulePackage
from schemas.creative_schemas import AssetPackage
from agents.launch_agent import run_launch_agent

router = APIRouter()

class LaunchRequest(BaseModel):
    schedule_package: SchedulePackage
    asset_package: AssetPackage

@router.post("/simulate")
async def simulate_campaign_launch(request: LaunchRequest):
    """
    Receives a schedule and asset package, then invokes the Launch Agent
    to run a full campaign simulation.
    """
    try:
        result = await run_launch_agent(
            schedule_package_dict=request.schedule_package.model_dump(),
            asset_package_dict=request.asset_package.model_dump()
        )
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during launch simulation: {str(e)}")

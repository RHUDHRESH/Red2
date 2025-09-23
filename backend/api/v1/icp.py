from fastapi import APIRouter, HTTPException, Body
from agents.icp_builder_agent import run_icp_builder_agent
from schemas.geo_schemas import MarketNeedReport
from schemas.icp_schemas import ICPReport

router = APIRouter()

@router.post("/build", response_model=ICPReport)
async def build_icps_from_report(market_report: MarketNeedReport = Body(...)):
    """
    Receives a MarketNeedReport and triggers the ICP Builder Agent.
    Returns the generated ICPs and Cohorts.
    """
    try:
        # The agent expects a dictionary, so we convert the Pydantic model
        result_dict = await run_icp_builder_agent(market_report.model_dump())
        
        if "error" in result_dict:
            raise HTTPException(status_code=500, detail=result_dict["error"])
        
        # We parse the result back into a Pydantic model for response validation
        return ICPReport(**result_dict)

    except Exception as e:
        # Catch any other unexpected errors during the process
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

from fastapi import APIRouter, HTTPException
from schemas.icp_schemas import ICPReport
from agents.cohort_agent import run_cohort_strategist_agent

router = APIRouter()

@router.post("/strategize",
    summary="Generate Marketing Strategies for Cohorts",
    description="Takes a full ICP Report and enriches each cohort with AI-generated marketing strategies."
)
async def get_cohort_strategies(report: ICPReport):
    """
    This endpoint receives an ICP report, passes it to the Cohort Strategist Agent,
    and returns the enriched report containing actionable marketing ideas.
    """
    try:
        # The agent expects a dictionary, so we convert the Pydantic model
        result = await run_cohort_strategist_agent(report.dict())
        
        # Check if the agent itself returned an error
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
            
        return result
    except Exception as e:
        # Catch any other unexpected errors during the process
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

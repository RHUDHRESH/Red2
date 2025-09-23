from fastapi import APIRouter, HTTPException

from agents.agent_hub import run_workflow
from schemas.a2a_schemas import WorkflowRequest, WorkflowResult


router = APIRouter()


@router.post("/run", response_model=WorkflowResult)
async def run_workflow_ep(req: WorkflowRequest):
    try:
        return await run_workflow(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Workflow error: {e}")


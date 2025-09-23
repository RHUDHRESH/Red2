from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agents.deep_research_agent import run_deep_research
from schemas.research_schemas import ResearchRequest, ResearchResponse

router = APIRouter()


@router.post("/deep", response_model=ResearchResponse)
async def deep_research(request: ResearchRequest):
    """Run the deep research agent: plan → search → fetch → summarize → synthesize.

    Returns concise findings with citations and per-source notes.
    """
    try:
        result = await run_deep_research(request.model_dump())
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected research error: {str(e)}")


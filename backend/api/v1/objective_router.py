from fastapi import APIRouter, HTTPException

from agents.objective_router_agent import run_objective_router
from schemas.objective_router_schemas import ObjectiveRouterRequest, ObjectiveRouterResponse
from services.pdf_writer_service import make_simple_pdf_base64


router = APIRouter()


@router.post("/run", response_model=ObjectiveRouterResponse)
async def run_router(req: ObjectiveRouterRequest):
    try:
        result = await run_objective_router(req.model_dump())
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Objective router error: {e}")


@router.post("/plan-pdf")
async def router_plan_pdf(req: ObjectiveRouterRequest):
    try:
        router_out = await run_objective_router(req.model_dump())
        plan = router_out.get("objective_router_v1", {})
        title = f"Objective Plan — {plan.get('classifications', {}).get('canonical_objective', '')}"
        body = []
        body.append(f"Objective: {plan.get('inputs', {}).get('objective', '')}")
        body.append(f"Business: {plan.get('inputs', {}).get('business_type', '')}")
        body.append(f"North Star: {plan.get('classifications', {}).get('north_star', '')}")
        ad = plan.get('ADAPT_plan', {})
        body.append("\nAlign:\n" + str(ad.get('align', {})))
        body.append("\nDiagnose:\n" + str(ad.get('diagnose', {})))
        body.append("\nArchitect:\n" + str(ad.get('architect', {})))
        body.append("\nPilot:\n" + str(ad.get('pilot', {})))
        body.append("\nTrack:\n" + str(ad.get('track', {})))
        pdf_b64 = make_simple_pdf_base64(title, "\n".join(body))
        return {"pdf_base64": pdf_b64, "router": router_out}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Plan PDF error: {e}")

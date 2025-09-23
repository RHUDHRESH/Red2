from fastapi import APIRouter, HTTPException

from agents.evidence_linker_agent import run_copy_evidence_audit
from schemas.evidence_schemas import CopyAuditRequest, CopyAuditResponse, RewriteApplyRequest, RewriteApplyResponse
import re


router = APIRouter()


@router.post("/audit", response_model=CopyAuditResponse)
async def audit_copy(req: CopyAuditRequest):
    try:
        result = await run_copy_evidence_audit(req.model_dump())
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected evidence audit error: {e}")


@router.post("/rewrite-apply", response_model=RewriteApplyResponse)
async def apply_rewrites(req: RewriteApplyRequest):
    try:
        text = req.copy_text
        for ch in req.changes:
            try:
                pattern = re.escape(ch.old)
                text = re.sub(pattern, ch.new, text, count=1)
            except Exception:
                continue
        return RewriteApplyResponse(revised_text=text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected rewrite apply error: {e}")

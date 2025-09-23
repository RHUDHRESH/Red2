from fastapi import APIRouter, HTTPException

from agents.permission_ladder_agent import build_permission_ladder
from schemas.permission_ladder_schemas import PermissionLadderRequest, PermissionLadderResponse


router = APIRouter()


@router.post("/blueprint", response_model=PermissionLadderResponse)
async def build_blueprint_ep(req: PermissionLadderRequest):
    try:
        return build_permission_ladder(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


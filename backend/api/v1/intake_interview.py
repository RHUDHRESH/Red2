
from fastapi import APIRouter, HTTPException
from agents.dynamic_intake_agent import run_dynamic_intake_turn, QUESTION_LIBRARIES
from schemas.dynamic_intake_schemas import (
    DynamicStartRequest,
    DynamicStartResponse,
    DynamicTurnRequest,
    DynamicTurnResponse,
    PersonaProfile,
)

router = APIRouter()


@router.post("/dynamic/start", response_model=DynamicStartResponse)
async def dynamic_start(req: DynamicStartRequest):
    """Fast start: avoid LLM call; ask the first high-signal question immediately."""
    try:
        lib = QUESTION_LIBRARIES.get("unknown", {})
        # pick the first slot deterministically for snappy UX
        first_slot = next(iter(lib.keys())) if lib else ""
        first_question = lib.get(first_slot, "Who are you and what do you do?")
        persona = PersonaProfile(persona_label="unknown", digital_footprint="medium", confidence=0.0, notes="")
        missing = [k for k in lib.keys() if k and k != first_slot]
        return DynamicStartResponse(persona=persona, first_question=first_question, missing_slots=missing)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start dynamic intake: {e}")


@router.post("/dynamic/message", response_model=DynamicTurnResponse)
async def dynamic_message(req: DynamicTurnRequest):
    try:
        turn = await run_dynamic_intake_turn(req.hints.model_dump(), history=req.history, user_message=req.user_message)
        return turn
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process message: {e}")

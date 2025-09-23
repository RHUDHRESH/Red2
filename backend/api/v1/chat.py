from fastapi import APIRouter, HTTPException
from typing import List
from fastapi.responses import StreamingResponse

from agents.chat_orchestrator import run_chat_orchestrator, stream_chat_events
from schemas.chat_schemas import ChatTurnRequest, ChatTurnResponse


router = APIRouter()


@router.post("/complete", response_model=ChatTurnResponse)
async def chat_complete(req: ChatTurnRequest):
    try:
        return await run_chat_orchestrator(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected chat error: {e}")


@router.get("/tools")
async def chat_tools() -> List[dict]:
    return [
        {"name": "research", "desc": "Deep research with citations"},
        {"name": "social_calendar", "desc": "Draft social posting plan"},
        {"name": "offer_assets", "desc": "Ad copy, image prompt, thread"},
        {"name": "evidence_audit", "desc": "Link claims to evidence and rewrites"},
        {"name": "schedule", "desc": "Create calendar ICS event"},
        {"name": "email_draft", "desc": "Draft an email for you to send"},
        {"name": "pdf_brief", "desc": "Generate a PDF brief"},
        {"name": "map_lookup", "desc": "Lookup maps (placeholder)"},
    ]


@router.post("/stream")
async def chat_stream(req: ChatTurnRequest):
    async def gen():
        async for chunk in stream_chat_events(req):
            yield chunk
    return StreamingResponse(gen(), media_type="text/event-stream")

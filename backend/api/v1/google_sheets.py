from __future__ import annotations

from typing import List, Optional, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.registry import get_services


router = APIRouter()


class GetValuesRequest(BaseModel):
    spreadsheet_id: str
    range_a1: str


class AppendValuesRequest(BaseModel):
    spreadsheet_id: str
    range_a1: str
    values: List[List[Any]] = Field(default_factory=list)
    value_input_option: str = "USER_ENTERED"


@router.get("/status")
async def status():
    sheets = get_services().sheets
    connected = sheets.is_connected()
    resp = {"connected": connected}
    if not connected:
        resp["connect_link"] = sheets.connect_link()
    return resp


@router.get("/connect-link")
async def connect_link():
    try:
        url = get_services().sheets.connect_link()
        return {"url": url}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/get-values")
async def get_values(req: GetValuesRequest):
    try:
        vals = await get_services().sheets.get_values(req.spreadsheet_id, req.range_a1)
        return {"values": vals}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/append-values")
async def append_values(req: AppendValuesRequest):
    try:
        data = await get_services().sheets.append_values(
            req.spreadsheet_id, req.range_a1, req.values, value_input_option=req.value_input_option
        )
        return {"status": "ok", "result": data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


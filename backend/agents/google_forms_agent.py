from __future__ import annotations

from typing import Dict

from schemas.normalized import Asset
from services.registry import get_services


async def create_simple_form(title: str, description: str = "") -> Dict:
    forms = get_services().gforms
    if not forms.is_connected():
        return {"error": "Google Forms not connected", "connect_link": forms.connect_link()}
    form = await forms.create_form(title, description)
    return {"form": form}


async def fetch_form_responses(form_id: str) -> Dict:
    forms = get_services().gforms
    if not forms.is_connected():
        return {"error": "Google Forms not connected", "connect_link": forms.connect_link()}
    resp = await forms.get_responses(form_id)
    return {"responses": resp}


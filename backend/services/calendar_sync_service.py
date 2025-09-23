from __future__ import annotations

import time
from typing import Dict, List

from .google_calendar_service import GoogleCalendarService
from schemas.normalized import Event


class CalendarSyncService:
    """Local event store with sync to Google Calendar.

    Stores events in-memory for dev. Replace with DB for production.
    """

    def __init__(self, gcal: GoogleCalendarService) -> None:
        self._gcal = gcal
        self._events: Dict[str, Event] = {}

    def upsert_local(self, ev: Event) -> Event:
        self._events[ev.id] = ev
        return ev

    def list_local(self) -> List[Event]:
        return list(self._events.values())

    async def sync_to_google(self, calendar_id: str = "primary") -> Dict[str, int]:
        created = 0
        updated = 0
        if not self._gcal.is_connected():
            return {"created": 0, "updated": 0}
        for ev in list(self._events.values()):
            payload = {
                "summary": ev.title,
                "description": ev.description or "",
                "location": ev.location or "",
                "start": {"dateTime": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ev.start_ts)), "timeZone": "UTC"},
                "end": {"dateTime": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ev.end_ts)), "timeZone": "UTC"},
            }
            if ev.external_id:
                await self._gcal.update_event(ev.external_id, payload, calendar_id=calendar_id)
                updated += 1
            else:
                res = await self._gcal.create_event(payload, calendar_id=calendar_id)
                ev.external_id = res.get("id")
                created += 1
        return {"created": created, "updated": updated}


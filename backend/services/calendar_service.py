from __future__ import annotations

from datetime import datetime


def build_ics_event(summary: str, description: str, start_iso: str, end_iso: str, location: str = "") -> str:
    def fmt(dt: str) -> str:
        # expects ISO, converts to UTC-like 20250101T130000Z (no TZ conversion here)
        try:
            d = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        except Exception:
            d = datetime.utcnow()
        return d.strftime("%Y%m%dT%H%M%SZ")

    uid = f"uid-{datetime.utcnow().timestamp()}@local"
    start = fmt(start_iso)
    end = fmt(end_iso)
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//GeoStrategist//EN",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{fmt(datetime.utcnow().isoformat())}",
        f"DTSTART:{start}",
        f"DTEND:{end}",
        f"SUMMARY:{summary}",
        f"DESCRIPTION:{description}",
        f"LOCATION:{location}",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    return "\r\n".join(lines)


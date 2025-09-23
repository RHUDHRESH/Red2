from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, EmailStr
import os
import base64
import smtplib
from email.message import EmailMessage

from services.calendar_service import build_ics_event
from services.registry import get_services
from schemas.canva_schemas import CanvaDesignRequest, CanvaDesignResponse


router = APIRouter()


class SendEmailRequest(BaseModel):
    to: EmailStr
    subject: str
    body: str
    attachments: list[dict] = Field(default_factory=list)  # {name,mime,base64}


@router.post("/send-email")
async def send_email(req: SendEmailRequest):
    try:
        host = os.getenv("SMTP_HOST")
        port = int(os.getenv("SMTP_PORT" ,"587"))
        user = os.getenv("SMTP_USER")
        password = os.getenv("SMTP_PASS")
        use_tls = os.getenv("SMTP_TLS", "1") == "1"
        if not host or not user or not password:
            raise HTTPException(status_code=400, detail="SMTP not configured")
        msg = EmailMessage()
        msg["Subject"] = req.subject
        msg["From"] = user
        msg["To"] = req.to
        msg.set_content(req.body)
        for a in req.attachments:
            try:
                data = base64.b64decode(a.get("base64", ""))
                maintype, subtype = (a.get("mime", "application/octet-stream").split("/", 1) + ["octet-stream"])[:2]
                msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=a.get("name", "attach"))
            except Exception:
                continue
        with smtplib.SMTP(host, port) as s:
            if use_tls:
                s.starttls()
            s.login(user, password)
            s.send_message(msg)
        return {"status": "sent"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SMTP error: {e}")


class GCalLinkRequest(BaseModel):
    title: str
    description: str
    start_iso: str
    end_iso: str
    location: str = ""


@router.post("/google-calendar-link")
async def gcal_link(req: GCalLinkRequest):
    try:
        # Google Calendar quick add URL
        import urllib.parse as up
        def fmt(dt: str) -> str:
            # 20250101T130000Z
            from datetime import datetime
            d = datetime.fromisoformat(dt.replace("Z", "+00:00"))
            return d.strftime("%Y%m%dT%H%M%SZ")
        start = fmt(req.start_iso)
        end = fmt(req.end_iso)
        params = {
            "action": "TEMPLATE",
            "text": req.title,
            "details": req.description,
            "location": req.location,
            "dates": f"{start}/{end}",
        }
        url = "https://calendar.google.com/calendar/render?" + up.urlencode(params)
        return {"url": url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Calendar link error: {e}")


class ICSRequest(BaseModel):
    title: str
    description: str
    start_iso: str
    end_iso: str
    location: str = ""


@router.post("/create-ics")
async def create_ics(req: ICSRequest):
    try:
        ics = build_ics_event(req.title, req.description, req.start_iso, req.end_iso, req.location)
        return {"base64": base64.b64encode(ics.encode()).decode("ascii")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ICS error: {e}")


@router.get("/canva/template-link")
async def canva_template_link():
    try:
        svc = get_services().canva
        url = svc.get_handoff_link()
        if not url:
            raise HTTPException(status_code=404, detail="CANVA_TEMPLATE_URL not configured")
        return {"template_link": url}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Canva error: {e}")


@router.post("/canva/design-brief", response_model=CanvaDesignResponse)
async def canva_design_brief(req: CanvaDesignRequest):
    try:
        from agents.canva_agent import run_canva_design
        res = await run_canva_design(req)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Canva design error: {e}")


# Connector status and metrics

@router.get("/connectors/status")
async def connectors_status():
    s = get_services()
    # register known connectors each call (idempotent)
    for name in [
        "google_sheets",
        "google_docs",
        "google_forms",
        "google_calendar",
        "gmail",
        "youtube_data",
        "ga4",
        "notion",
        "discord",
    ]:
        s.connectors.register(name)
    return s.connectors.list()

@router.get("/connectors/metrics")
async def connectors_metrics():
    return get_services().metrics.all()

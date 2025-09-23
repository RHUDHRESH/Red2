from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from typing import Optional

from services.registry import get_services


router = APIRouter()


@router.get("/providers")
async def list_providers():
    svc = get_services().oauth
    info = svc.providers_info()
    # Provide an authorize link stub (uid=default) for convenience
    out = {}
    for name, meta in info.items():
        try:
            url = svc.build_authorize_url(name, uid="default") if meta["enabled"] else None
        except Exception:
            url = None
        out[name] = {**meta, "authorize_link": url}
    return out


@router.get("/authorize/{provider}")
async def authorize(provider: str, uid: Optional[str] = "default", redirect: Optional[int] = 0):
    svc = get_services().oauth
    try:
        url = svc.build_authorize_url(provider, uid or "default")
        if redirect == 1:
            return RedirectResponse(url)
        return {"url": url}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/callback/{provider}")
async def callback(provider: str, request: Request, code: Optional[str] = None, state: Optional[str] = None, error: Optional[str] = None):
    svc = get_services().oauth
    if error:
        raise HTTPException(status_code=400, detail=f"OAuth error: {error}")
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code/state")
    data = svc.consume_state(state)
    if not data or data.get("provider") != provider:
        raise HTTPException(status_code=400, detail="Invalid state")
    uid = data.get("uid") or "default"
    try:
        token = await svc.exchange_code(provider, code)
        svc.save_token(uid, provider, token)
        # Minimal success page for popup-based flow
        html = """
        <html><body>
        <p>Connected successfully. You can close this window.</p>
        <script>setTimeout(()=>window.close(), 800);</script>
        </body></html>
        """
        return HTMLResponse(content=html)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{provider}")
async def status(provider: str, uid: Optional[str] = "default"):
    svc = get_services().oauth
    tok = svc.get_token(uid or "default", provider)
    return {"connected": bool(tok), "provider": provider, "uid": uid, "scopes": (tok.scope.split(" ") if tok and tok.scope else [])}


@router.post("/revoke/{provider}")
async def revoke(provider: str, uid: Optional[str] = "default"):
    svc = get_services().oauth
    svc.revoke(uid or "default", provider)
    return {"status": "revoked", "provider": provider, "uid": uid}


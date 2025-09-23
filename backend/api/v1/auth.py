from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from typing import Optional

from services.registry import get_services


SESSION_COOKIE = "gs_session"

router = APIRouter()


def _cookie(response: Response, token: str, *, delete: bool = False) -> None:
    if delete:
        response.delete_cookie(SESSION_COOKIE)
        return
    # Lax for same-site usage, HttpOnly, not Secure in local dev
    response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="lax")


@router.get("/login/google")
async def login_google(redirect: Optional[int] = 1):
    url = get_services().oauth.build_authorize_url("google", uid="owner")
    if redirect:
        return RedirectResponse(url)
    return {"url": url}


@router.get("/callback/google")
async def callback_google(request: Request, code: Optional[str] = None, state: Optional[str] = None):
    oauth = get_services().oauth
    users = get_services().users
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code/state")
    data = oauth.consume_state(state)
    if not data or data.get("provider") != "google":
        raise HTTPException(status_code=400, detail="Invalid state")
    try:
        token = await oauth.exchange_code("google", code)
        oauth.save_token("owner", "google", token)
        # Fetch Google userinfo (OpenID)
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get("https://openidconnect.googleapis.com/v1/userinfo", headers={"Authorization": f"Bearer {token.access_token}"})
            r.raise_for_status()
            info = r.json()
        sub = info.get("sub")
        if not sub:
            raise HTTPException(status_code=400, detail="Missing 'sub' from userinfo")
        email = info.get("email", "")
        name = info.get("name", "")
        picture = info.get("picture")
        user = users.upsert_user_google(sub=sub, email=email, name=name, picture=picture)
        # Create local session and set cookie
        session = users.create_session(user.id)
        html = f"""
        <html><body>
        <p>Signed in as {user.name or user.email}. You can close this window.</p>
        <script>
          try {{ document.cookie = '{SESSION_COOKIE}={session}; path=/; SameSite=Lax'; }} catch (e) {{}}
          setTimeout(()=>window.close(), 800);
        </script>
        </body></html>
        """
        resp = HTMLResponse(content=html)
        # Also set cookie server-side for robustness
        resp.set_cookie(SESSION_COOKIE, session, httponly=True, samesite="lax")
        return resp
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/me")
async def me(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return JSONResponse({"authenticated": False})
    user = get_services().users.get_user_by_session(token)
    if not user:
        return JSONResponse({"authenticated": False})
    return {
        "authenticated": True,
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "picture": user.picture,
        "owner": user.is_owner,
        "provider": user.provider,
    }


@router.post("/logout")
async def logout(request: Request, response: Response):
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        get_services().users.revoke_session(token)
        _cookie(response, token, delete=True)
    return {"status": "ok"}

from fastapi import APIRouter, Request
from core.config import settings
import httpx
import shutil
import asyncio
import sys

try:
    import fastapi as _fastapi_mod  # type: ignore
except Exception:  # pragma: no cover
    _fastapi_mod = None
try:
    import chromadb as _chroma_mod  # type: ignore
except Exception:  # pragma: no cover
    _chroma_mod = None
try:
    import langchain_ollama as _lc_ollama  # type: ignore
except Exception:  # pragma: no cover
    _lc_ollama = None

router = APIRouter()


@router.get("/public")
async def public_config(request: Request):
    """Expose non-sensitive runtime config for the frontend.

    - backend_url: derived from request base URL (handy for clients)
    - google_maps_api_key: browser key if configured; optionally server key if enabled for local dev
    """
    base_url = str(request.base_url).rstrip("/")
    maps_key = settings.GOOGLE_MAPS_BROWSER_API_KEY
    if not maps_key and settings.EXPOSE_SERVER_MAPS_KEY_TO_FRONTEND:
        # Only expose if a real server key is present (avoid placeholders)
        if settings.GOOGLE_MAPS_API_KEY and "your_actual" not in settings.GOOGLE_MAPS_API_KEY:
            maps_key = settings.GOOGLE_MAPS_API_KEY
    return {"backend_url": base_url, "google_maps_api_key": maps_key or None}


@router.get("/health/details")
async def health_details(request: Request):
    """Return detailed runtime health information for frontend preflight.

    - backend: always ok if this route is reachable
    - maps: presence of server/browser keys
    - ollama: reachable and whether configured models are available
    - chroma: HTTP heartbeat on configured host/port
    """
    base_url = str(request.base_url).rstrip("/")

    # Maps
    maps = {
        "server_key_present": bool(settings.GOOGLE_MAPS_API_KEY and "your_actual" not in settings.GOOGLE_MAPS_API_KEY),
        "browser_key_present": bool(settings.GOOGLE_MAPS_BROWSER_API_KEY),
    }

    # Ollama
    ollama = {
        "reachable": False,
        "fast_model_available": False,
        "reasoning_model_available": False,
        "embeddings_model_available": False,
        "base_url": settings.OLLAMA_BASE_URL,
        "requested_models": {
            "fast": settings.OLLAMA_FAST_MODEL,
            "reasoning": settings.OLLAMA_REASONING_MODEL,
            "embeddings": settings.OLLAMA_EMBEDDINGS_MODEL,
        },
        "available_models": [],
    }
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            r = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            if r.status_code == 200:
                ollama["reachable"] = True
                data = r.json()
                models = data.get("models", [])
                tags = {m.get("name") for m in models}
                ollama["available_models"] = sorted(tags)
                ollama["fast_model_available"] = settings.OLLAMA_FAST_MODEL in tags
                ollama["reasoning_model_available"] = settings.OLLAMA_REASONING_MODEL in tags
                # Embeddings model may be served as a tag as well
                ollama["embeddings_model_available"] = settings.OLLAMA_EMBEDDINGS_MODEL in tags
    except Exception:
        pass

    # Chroma
    chroma = {
        "reachable": False,
        "host": settings.CHROMA_HOST,
        "port": settings.CHROMA_PORT,
    }
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            r = await client.get(f"http://{settings.CHROMA_HOST}:{settings.CHROMA_PORT}/api/v1/heartbeat")
            chroma["reachable"] = r.status_code == 200
    except Exception:
        pass

    versions = {
        "python": sys.version.split(" ")[0],
        "fastapi": getattr(_fastapi_mod, "__version__", None),
        "httpx": getattr(httpx, "__version__", None),
        "chromadb": getattr(_chroma_mod, "__version__", None) if _chroma_mod else None,
        "langchain_ollama": getattr(_lc_ollama, "__version__", None) if _lc_ollama else None,
    }

    runtime = {
        "node_present": bool(shutil.which("node") or shutil.which("node.exe")),
        "npm_present": bool(shutil.which("npm") or shutil.which("npm.cmd")),
        "java_present": bool(shutil.which("java") or shutil.which("java.exe")),
    }

    return {
        "backend": {"ok": True, "url": base_url},
        "maps": maps,
        "ollama": ollama,
        "chroma": chroma,
        "versions": versions,
        "runtime": runtime,
    }


@router.get("/flight-check")
async def flight_check(request: Request):
    """Aggregated preflight for UI: health details + tools list + quick tips."""
    base_url = str(request.base_url).rstrip("/")

    # Reuse health details
    details = await health_details(request)

    # Tool list (keep in sync with chat.tools)
    tools = [
        {"name": "research", "desc": "Deep research with citations"},
        {"name": "social_calendar", "desc": "Draft social posting plan"},
        {"name": "offer_assets", "desc": "Ad copy, image prompt, thread"},
        {"name": "evidence_audit", "desc": "Link claims to evidence and rewrites"},
        {"name": "schedule", "desc": "Create calendar ICS event"},
        {"name": "email_draft", "desc": "Draft an email for you to send"},
        {"name": "pdf_brief", "desc": "Generate a PDF brief"},
        {"name": "map_lookup", "desc": "Lookup maps (placeholder)"},
    ]

    return {
        **details,
        "frontend": {
            "vite_url": "http://localhost:5173",
            "docs_url": f"{base_url}/docs",
        },
        "tools": tools,
        "tips": [
            "Run web UI via: npm install && npm run dev (in geo_strategist_app/web)",
            "Start backend via: python geo_strategist_app/backend/main.py",
        ],
    }


@router.get("/catalog")
async def catalog(request: Request):
    """Return a lightweight catalog of available agent endpoints for the UI.

    This is intentionally curated rather than auto-generated from OpenAPI to keep
    the frontend simple while exposing all major agents and their entrypoints.
    """
    base = str(request.base_url).rstrip("/")

    def ep(path: str, method: str = "POST", sample_payload: dict | None = None):
        return {"path": path, "method": method, "sample_payload": sample_payload}

    agents = [
        {
            "key": "intake_dynamic",
            "title": "Dynamic Intake",
            "description": "Conversational intake to gather facts/claims.",
            "base": f"{base}/api/v1/intake",
            "endpoints": [
                ep("/dynamic/start", "POST", {"hints": {}}),
                ep("/dynamic/message", "POST", {"history": ["First question asked"], "user_message": "Your reply", "hints": {}}),
            ],
        },
        {
            "key": "positioning",
            "title": "Positioning Agent",
            "description": "Generate and validate 3 positioning options.",
            "base": f"{base}/api/v1/positioning",
            "endpoints": [
                ep("/generate-options", "POST", {"facts": ["..."], "claims": ["..."], "taboos": []}),
            ],
        },
        {
            "key": "icp_builder",
            "title": "ICP Builder",
            "description": "Build ideal customer profiles from a market report.",
            "base": f"{base}/api/v1/icp",
            "endpoints": [
                ep("/build", "POST", {
                    "demand_hotspots": [{"poi_name": "Campus Center", "poi_type": "university", "headcount": 10000, "distance_m": 300, "travel_time_min": 5, "reach_score": 0.8, "latitude": 0.0, "longitude": 0.0}],
                    "competitor_count": 3, "median_price": 12, "price_gap_pct": 0.1, "pain_topics": {"slow": 0.7}, "final_score": 0.74, "verdict": "PASS"
                }),
            ],
        },
        {
            "key": "seo_brief",
            "title": "SEO Brief",
            "description": "Generate a structured SEO content brief.",
            "base": f"{base}/api/v1/seo",
            "endpoints": [
                ep("/brief", "POST", {"topic": "", "audience": "", "goals": ["traffic"], "constraints": []}),
            ],
        },
        {
            "key": "strategy_engine",
            "title": "Strategy Engine",
            "description": "Run strategy primitives (segment, wound, reframe, offer, action, cash, etc.)",
            "base": f"{base}/api/v1/strategy",
            "endpoints": [
                ep("/run/segment", "POST", {"context": "..."}),
                ep("/run/wound", "POST", {"context": "..."}),
                ep("/run/reframe", "POST", {"context": "..."}),
                ep("/run/offer", "POST", {"context": "..."}),
            ],
        },
        {
            "key": "social_calendar",
            "title": "Social Calendar",
            "description": "Draft a social posting calendar.",
            "base": f"{base}/api/v1/social-calendar",
            "endpoints": [ep("/build", "POST", {"objective": "...", "channels": ["twitter"], "cadence": "daily"})],
        },
        {
            "key": "creatives",
            "title": "Creative Director",
            "description": "Generate assets from a strike plan and outcome charter.",
            "base": f"{base}/api/v1/creatives",
            "endpoints": [ep("/generate-assets", "POST", {"strike_plan": {"title": "..."}, "outcome_charter": {"title": "..."}})],
        },
        {
            "key": "research",
            "title": "Research",
            "description": "Deep research with citations.",
            "base": f"{base}/api/v1/research",
            "endpoints": [ep("/deep", "POST", {"query": "..."})],
        },
        {
            "key": "objective_router",
            "title": "Objective Router",
            "description": "Route objectives to the right agent(s).",
            "base": f"{base}/api/v1/objective-router",
            "endpoints": [ep("/route", "POST", {"objective": "..."})],
        },
        {
            "key": "a2a",
            "title": "Agent-to-Agent Workflow",
            "description": "Run multi-agent workflows.",
            "base": f"{base}/api/v1/a2a",
            "endpoints": [ep("/run", "POST", {"workflow": "name", "inputs": {}})],
        },
    ]

    return {"agents": agents}

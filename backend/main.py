import os
import sys
import subprocess
import shutil
import webbrowser
import time
import logging

# Early bootstrap for critical deps (before third-party imports)
# Removed early bootstrap for critical deps to prevent installation conflicts with venv
# The script now relies on start.bat to handle installations properly

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from fastapi.exceptions import RequestValidationError

from core.config import settings
from services.registry import init_services, shutdown_services
from api.v1 import (
    geo_analysis,
    intake_interview,
    positioning,
    objection,
    icp,
    cohorts,
    outcomes,
    moves,
    creatives,
    assets,
    scheduler,
    launch,
    archive,
    competitors,
    research,
    seo,
    partners,
    social_calendar,
    landing,
    evidence,
    synthetic,
    synthetic_pipeline,
    ops,
    strategy,
    chat,
    a2a,
    objective_router,
    integrations,
    oauth as oauth_api,
    auth as auth_api,
    google_sheets as gs_api,
    config as public_config,
)
from api.v1 import (
    neurofoundry as neuro_api,
    permission_ladder as ladder_api,
    rok as rok_api,
    founder_brand as founder_api,
    intake_orchestration as intake_auto,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Geo-Strategist AI API",
    description="Backend services for the local-first strategic marketing application.",
    version="1.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)


def _ensure_node() -> bool:
    node = shutil.which("node") or shutil.which("node.exe")
    npm = shutil.which("npm") or shutil.which("npm.cmd")
    return bool(node and npm)


def _start_frontend_dev():
    if os.getenv("AUTO_FRONTEND", "1") != "1":
        return
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    web_dir = os.path.join(root, "web")
    if not os.path.isdir(web_dir):
        return
    if not _ensure_node():
        print("[frontend] Node/npm not found; skipping Vite dev server.")
        return
    flags = subprocess.CREATE_NEW_CONSOLE if os.name == "nt" else 0
    try:
        # Install dependencies only if node_modules missing to speed up startup
        if not os.path.isdir(os.path.join(web_dir, "node_modules")):
            subprocess.Popen(["npm", "install", "--no-audit", "--progress=false"], cwd=web_dir, creationflags=flags)
        subprocess.Popen(["npm", "run", "dev"], cwd=web_dir, creationflags=flags)
        time.sleep(1)
        if os.getenv("AUTO_OPEN_BROWSER", "1") == "1":
            webbrowser.open("http://localhost:5173")
    except Exception:
        pass


# Return rich 422 errors with fields and locations
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "message": "Validation failed",
            "error_count": len(exc.errors()),
            "errors": exc.errors(),
            "path": str(request.url),
        },
    )


@app.get("/api/v1/health", tags=["Status"])
async def health_check():
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def root_landing():
    base = settings.PUBLIC_BASE_URL.rstrip("/")
    html = """
    <!doctype html>
    <html>
    <head>
      <meta charset='utf-8'/>
      <meta name='viewport' content='width=device-width, initial-scale=1'/>
      <title>Geo-Strategist API</title>
      <style>
        body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 40px; color: #111; }}
        .card {{ max-width: 820px; padding: 24px; border: 1px solid #e5e7eb; border-radius: 12px; box-shadow: 0 1px 2px rgba(0,0,0,0.04); }}
        .btn {{ display: inline-block; margin-right: 8px; margin-bottom: 8px; padding: 10px 14px; background: #111827; color: #fff; border-radius: 8px; text-decoration: none; }}
        .btn.light {{ background: #4f46e5; }}
        code {{ background: #f3f4f6; padding: 2px 6px; border-radius: 6px; }}
        .ok {{ color: #059669 }} .warn {{ color: #b45309 }} .bad {{ color: #b91c1c }}
        pre {{ background: #0b1021; color: #e5e7eb; padding: 12px; border-radius: 8px; overflow:auto; }}
      </style>
    </head>
    <body>
      <div class='card'>
        <h1>✅ Geo‑Strategist API is running</h1>
        <p>Quick links:</p>
        <p>
          <a class='btn' href='__BASE__/docs' target='_blank'>Open API Docs</a>
          <a class='btn light' href='http://localhost:5173' target='_blank'>Open Web UI (Vite)</a>
          <a class='btn' href='__BASE__/api/v1/config/health/details' target='_blank'>Health Details</a>
          <a class='btn' href='__BASE__/api/v1/config/flight-check' target='_blank'>Flight Check</a>
        </p>
        <h3>Status</h3>
        <div id='status'>Loading…</div>
        <script>
          async function refresh() {
            try {{
              const r = await fetch('__BASE__/api/v1/config/health/details');
              const j = await r.json();
              function b(v) { return v ? '<span class=ok>OK</span>' : '<span class=bad>MISSING</span>'; }
              document.getElementById('status').innerHTML = `
                <ul>
                  <li><b>Backend</b>: ${b(j.backend && j.backend.ok)}</li>
                  <li><b>Ollama</b>: ${b(j.ollama && j.ollama.reachable)}
                    <small>(fast: ${b(j.ollama && j.ollama.fast_model_available)}, reasoning: ${b(j.ollama && j.ollama.reasoning_model_available)}, embed: ${b(j.ollama && j.ollama.embeddings_model_available)})</small>
                  </li>
                  <li><b>ChromaDB</b>: ${b(j.chroma && j.chroma.reachable)} (http://${j.chroma && j.chroma.host}:${j.chroma && j.chroma.port})</li>
                  <li><b>Maps Key (server)</b>: ${b(j.maps && j.maps.server_key_present)} | <b>(browser)</b>: ${b(j.maps && j.maps.browser_key_present)}</li>
                </ul>`;
            } catch (e) {
              document.getElementById('status').innerHTML = '<span class=bad>Failed to load health details.</span>';
            }
          }
          refresh();
        </script>
        <details style='margin-top:14px'>
          <summary>How to run locally</summary>
          <pre>1) Backend
cd geo_strategist_app\\backend
python -m venv .venv && .\\.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
python .\\main.py

2) Web UI (Vite)
cd geo_strategist_app\\web
npm install && npm run dev

Open http://localhost:5173</pre>
        </details>
      </div>
    </body>
    </html>
    """.replace("__BASE__", base)
    return HTMLResponse(content=html)


# Include all modular API routers
app.include_router(geo_analysis.router, prefix="/api/v1/geo", tags=["Geo Analysis"])
app.include_router(intake_interview.router, prefix="/api/v1/intake", tags=["Intake Interview"])
app.include_router(intake_auto.router, prefix="/api/v1/intake", tags=["Intake Orchestration"])
app.include_router(positioning.router, prefix="/api/v1/positioning", tags=["Positioning"])
app.include_router(objection.router, prefix="/api/v1/objection", tags=["Objection Handling"])
app.include_router(icp.router, prefix="/api/v1/icp", tags=["ICP Builder"])
app.include_router(cohorts.router, prefix="/api/v1/cohorts", tags=["Cohort Strategy"])
app.include_router(outcomes.router, prefix="/api/v1/outcomes", tags=["Outcome Committer"])
app.include_router(moves.router, prefix="/api/v1/moves", tags=["Move Maker"])
app.include_router(creatives.router, prefix="/api/v1/creatives", tags=["Creative Director"]) 
app.include_router(assets.router, prefix="/api/v1/assets", tags=["Assets"]) 
app.include_router(scheduler.router, prefix="/api/v1/scheduler", tags=["Scheduler"])
app.include_router(launch.router, prefix="/api/v1/launch", tags=["Launch & Nurture"])
app.include_router(archive.router, prefix="/api/v1/archive", tags=["Template Archive"]) 
app.include_router(competitors.router, prefix="/api/v1/competitors", tags=["Competitor Intel"]) 
app.include_router(research.router, prefix="/api/v1/research", tags=["Research"]) 
app.include_router(seo.router, prefix="/api/v1/seo", tags=["SEO Briefs"]) 
app.include_router(partners.router, prefix="/api/v1/partners", tags=["Partnerships"]) 
app.include_router(social_calendar.router, prefix="/api/v1/social-calendar", tags=["Social Calendar"]) 
app.include_router(landing.router, prefix="/api/v1/landing", tags=["Landing Page"]) 
app.include_router(evidence.router, prefix="/api/v1/evidence", tags=["Evidence Audit"]) 
app.include_router(synthetic.router, prefix="/api/v1/synthetic", tags=["Synthetic Cohorts"]) 
app.include_router(synthetic_pipeline.router, prefix="/api/v1/synth-pipeline", tags=["Synthetic ICP Pipeline"]) 
app.include_router(ops.router, prefix="/api/v1/ops", tags=["Ops Copilot"]) 
app.include_router(strategy.router, prefix="/api/v1/strategy", tags=["Marketing Strategy"]) 
app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chatbot"]) 
app.include_router(a2a.router, prefix="/api/v1/a2a", tags=["Agent Hub"]) 
app.include_router(objective_router.router, prefix="/api/v1/objective-router", tags=["Objective Router"]) 
app.include_router(integrations.router, prefix="/api/v1/integrations", tags=["Integrations"]) 
app.include_router(oauth_api.router, prefix="/api/v1/oauth", tags=["OAuth"]) 
app.include_router(auth_api.router, prefix="/api/v1/auth", tags=["Auth"]) 
app.include_router(gs_api.router, prefix="/api/v1/google-sheets", tags=["Google Sheets"]) 
app.include_router(public_config.router, prefix="/api/v1/config", tags=["Config"]) 
app.include_router(neuro_api.router, prefix="/api/v1/neurofoundry", tags=["Neurofoundry"]) 
app.include_router(ladder_api.router, prefix="/api/v1/ladder", tags=["Permission Ladder"]) 
app.include_router(rok_api.router, prefix="/api/v1/rok", tags=["ROK Knife"]) 
app.include_router(founder_api.router, prefix="/api/v1/founder-brand", tags=["Founder Brand"]) 


@app.on_event("startup")
async def startup_event():
    logger.info("Starting up Geo-Strategist AI API...")
    gmaps_key_status = "OK" if settings.GOOGLE_MAPS_API_KEY and 'your_actual' not in settings.GOOGLE_MAPS_API_KEY else "NOT SET"
    logger.info(f"Google Maps API Key Status: {gmaps_key_status}")
    logger.info(f"Ollama URL: {settings.OLLAMA_BASE_URL}")

    # Initialize shared services so all agents reuse them
    try:
        services = init_services()
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        services = None

    # Dependency health checks (best-effort, non-fatal)
    try:
        # Ollama reachability and tags
        try:
            async with httpx.AsyncClient(timeout=2.5) as client:
                r = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
                if r.status_code == 200:
                    names = {m.get("name") for m in r.json().get("models", [])}
                    fast_ok = settings.OLLAMA_FAST_MODEL in names
                    reason_ok = settings.OLLAMA_REASONING_MODEL in names
                    embed_ok = settings.OLLAMA_EMBEDDINGS_MODEL in names
                    logger.info(
                        f"Ollama reachable. Models: fast={'OK' if fast_ok else 'MISSING'}, reasoning={'OK' if reason_ok else 'MISSING'}, embeddings={'OK' if embed_ok else 'MISSING'}"
                    )
                else:
                    logger.warning(f"Ollama responded with HTTP {r.status_code} at /api/tags")
        except Exception as e:
            logger.warning(f"Ollama not reachable at {settings.OLLAMA_BASE_URL}: {e}")

        # ChromaDB reachability via collection count
        try:
            if services and services.vectorstore is not None:
                count = services.vectorstore._collection.count()  # type: ignore[attr-defined]
                logger.info(f"ChromaDB reachable. Collection 'playbook_templates' count: {count}")
            else:
                logger.warning("ChromaDB client not initialized; start server on CHROMA_PORT and restart.")
        except Exception as e:
            logger.warning(f"ChromaDB not reachable at {settings.CHROMA_HOST}:{settings.CHROMA_PORT}: {e}")
    except Exception:
        # Never fail startup on health checks
        pass

    # Optionally open API docs in browser
    if os.getenv("AUTO_OPEN_BROWSER", "1") == "1":
        try:
            webbrowser.open(f"{settings.PUBLIC_BASE_URL.rstrip('/')}/docs")
        except Exception:
            pass


@app.on_event("shutdown")
async def shutdown_event():
    await shutdown_services()


if __name__ == "__main__":
    # Avoid runaway reload loops on Windows/OneDrive by default.
    # Enable reload explicitly by setting UVICORN_RELOAD=1.
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("UVICORN_RELOAD", "0") == "1"
    import uvicorn
    try:
        _start_frontend_dev()
    except Exception:
        pass
    uvicorn.run("main:app", host=host, port=port, reload=reload)

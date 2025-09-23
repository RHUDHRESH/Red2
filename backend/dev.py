#!/usr/bin/env python
"""
One-command local dev runner.

Tasks:
- Ensures venv + installs requirements
- Starts ChromaDB server on 8001
- Verifies Ollama + pulls models from .env
- Starts FastAPI backend (main.py)
- Opens the frontend with backend URL param

Usage examples:
  python dev.py start       # full cycle: bootstrap, start services, open frontend
  python dev.py bootstrap   # just create venv + install reqs
  python dev.py pull-models # just verify ollama + pull models
"""
from __future__ import annotations

import argparse
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]  # geo_strategist_app
BACKEND = Path(__file__).resolve().parent
FRONTEND = ROOT / "web"  # React app (Vite)
VENV = BACKEND / ".venv"

# Prefer an external venv when running under OneDrive to avoid
# Files On-Demand issues (Errno 22 on cloud-only files). Allow override.
_ext_venv = os.environ.get("DEV_VENV_DIR") or os.environ.get("VENV_DIR")
try:
    # Avoid referencing is_windows() here (defined later)
    _on_windows = platform.system().lower().startswith("win")
except Exception:
    _on_windows = False

if _ext_venv:
    VENV = Path(_ext_venv)
elif _on_windows and "onedrive" in str(BACKEND).lower():
    # Default external venv location on Windows
    _venv_home = os.environ.get("VENV_HOME", r"C:\\venvs")
    VENV = Path(_venv_home) / "geo_backend"


def is_windows() -> bool:
    return platform.system().lower().startswith("win")


def venv_bin(exe: str) -> str:
    if is_windows():
        return str(VENV / "Scripts" / f"{exe}.exe")
    return str(VENV / "bin" / exe)


def print_step(msg: str) -> None:
    print(f"\x1b[36m[STEP]\x1b[0m {msg}")


def print_ok(msg: str) -> None:
    print(f"\x1b[32m[ OK ]\x1b[0m {msg}")


def print_warn(msg: str) -> None:
    print(f"\x1b[33m[WARN]\x1b[0m {msg}")


def print_err(msg: str) -> None:
    print(f"\x1b[31m[ERR ]\x1b[0m {msg}")


def run(cmd: list[str], **kwargs) -> int:
    return subprocess.call(cmd, **kwargs)


def run_bg(cmd: list[str], cwd: Path | None = None, env: dict | None = None):
    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if is_windows() else 0
    return subprocess.Popen(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
        stdout=None,  # inherit parent console for live logs
        stderr=None,
        text=False,
        creationflags=creationflags,
    )


def wait_for_port(host: str, port: int, timeout_s: float = 20.0) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return True
        except OSError:
            time.sleep(0.3)
    return False


def bootstrap() -> None:
    print_step("Creating venv and installing requirements...")
    # Ensure parent dir exists for external venvs
    try:
        VENV.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    if not VENV.exists():
        code = run([sys.executable, "-m", "venv", str(VENV)])
        if code != 0:
            print_err("Failed to create virtualenv")
            sys.exit(code)
    py = venv_bin("python")
    code = run([py, "-m", "pip", "install", "--upgrade", "pip"], cwd=BACKEND)
    if code != 0:
        print_err("Failed to upgrade pip")
        sys.exit(code)
    code = run([py, "-m", "pip", "install", "-r", "requirements.txt"], cwd=BACKEND)
    if code != 0:
        print_err("Failed to install requirements")
        sys.exit(code)
    # Ensure HTTP/2 support for httpx (used by startup health checks)
    run([py, "-m", "pip", "install", "httpx[http2]"], cwd=BACKEND)
    # Optional extras for PDF/SDV
    print_step("Installing optional extras (reportlab, sdv) if available...")
    run([py, "-m", "pip", "install", "reportlab"], cwd=BACKEND)
    run([py, "-m", "pip", "install", "sdv", "pandas", "numpy", "scikit-learn", "copulas"], cwd=BACKEND)
    print_ok("Venv ready and requirements installed.")


def ensure_node() -> None:
    print_step("Checking Node.js + npm...")
    node = shutil.which("node") or shutil.which("node.exe")
    npm = shutil.which("npm") or shutil.which("npm.cmd")
    if node and npm:
        print_ok("Node/npm found.")
        return
    print_warn("Node/npm not found. Attempting install via common package managers...")
    if is_windows():
        winget = shutil.which("winget")
        if winget:
            run([winget, "install", "OpenJS.NodeJS.LTS", "-e", "--id", "OpenJS.NodeJS.LTS"])  # may require user consent
        else:
            print_warn("winget not available. Install Node LTS from https://nodejs.org/en/download ")
    else:
        brew = shutil.which("brew")
        apt = shutil.which("apt")
        if brew:
            run(["brew", "install", "node"])
        elif apt:
            run(["sudo", "apt", "update"]) ; run(["sudo", "apt", "install", "-y", "nodejs", "npm"])
        else:
            print_warn("Please install Node LTS manually: https://nodejs.org/en/download")


def ensure_java() -> None:
    print_step("Checking Java...")
    java = shutil.which("java") or shutil.which("java.exe")
    if java:
        print_ok("Java found.")
        return
    print_warn("Java not found. Attempting install via common package managers...")
    if is_windows():
        winget = shutil.which("winget")
        if winget:
            run([winget, "install", "EclipseAdoptium.Temurin.17.JRE", "-e", "--id", "EclipseAdoptium.Temurin.17.JRE"])  # headless JRE
        else:
            print_warn("winget not available. Install Java from https://adoptium.net/")
    else:
        brew = shutil.which("brew")
        apt = shutil.which("apt")
        if brew:
            run(["brew", "install", "temurin@17"])  # JDK
        elif apt:
            run(["sudo", "apt", "update"]) ; run(["sudo", "apt", "install", "-y", "default-jre"])
        else:
            print_warn("Please install Java 17+: https://adoptium.net/")


def ensure_env() -> dict:
    # Load .env-like variables minimal; the backend reads its own .env
    return os.environ.copy()


def pull_models() -> None:
    print_step("Verifying Ollama and pulling models from .env...")
    ollama = shutil.which("ollama")
    if not ollama:
        print_warn("Ollama not found in PATH. Install and run Ollama, then re-run.")
        return
    # Read models from backend .env (fallback to defaults)
    env_file = BACKEND / ".env"
    fast = "gemma3:1b"
    reason = "gemma3:4b"
    embed = "nomic-embed-text"
    if env_file.exists():
        text = env_file.read_text(encoding="utf-8")
        for line in text.splitlines():
            if line.startswith("OLLAMA_FAST_MODEL="):
                fast = line.split("=", 1)[1].strip().strip('"')
            if line.startswith("OLLAMA_REASONING_MODEL="):
                reason = line.split("=", 1)[1].strip().strip('"')
            if line.startswith("OLLAMA_EMBEDDINGS_MODEL="):
                embed = line.split("=", 1)[1].strip().strip('"')
    # Try listing (verifies daemon)
    run([ollama, "list"])  # ignore result; prints helpful message if daemon down
    run([ollama, "pull", fast])
    run([ollama, "pull", reason])
    run([ollama, "pull", embed])
    print_ok(f"Models ensured: {fast}, {reason}, {embed}")


def start_chroma(env: dict) -> subprocess.Popen:
    print_step("Starting ChromaDB on :8001...")
    chroma_exe = venv_bin("chroma")
    db_dir = BACKEND / "chroma_db"
    db_dir.mkdir(exist_ok=True)
    proc = run_bg([chroma_exe, "run", "--path", str(db_dir), "--host", "0.0.0.0", "--port", "8001"], cwd=BACKEND, env=env)
    if not wait_for_port("127.0.0.1", 8001, 20):
        print_warn("Chroma not reachable on :8001 yet; continuing...")
    else:
        print_ok("ChromaDB is up on :8001")
    return proc


def _first_free_port(candidates: list[int]) -> int | None:
    for p in candidates:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.3)
                if s.connect_ex(("127.0.0.1", p)) != 0:
                    return p
        except Exception:
            continue
    return None


def start_backend(env: dict) -> tuple[subprocess.Popen, int]:
    desired = int(env.get("PORT", "8000"))
    candidates = [desired] + [p for p in range(8001, 8011)]
    port = _first_free_port(candidates) or desired
    if str(port) != env.get("PORT", ""):
        env = dict(env)
        env["PORT"] = str(port)
    print_step(f"Starting FastAPI backend on :{port}...")
    py = venv_bin("python")
    proc = run_bg([py, "main.py"], cwd=BACKEND, env=env)
    if not wait_for_port("127.0.0.1", port, 30):
        print_warn(f"Backend not reachable on :{port} yet; continuing...")
    else:
        print_ok(f"Backend is up on :{port}")
    return proc, port


def start_frontend_dev(env: dict, backend_url: str) -> subprocess.Popen:
    ensure_node()
    npm_exe = shutil.which("npm") or shutil.which("npm.cmd")
    if not npm_exe:
        print_err("npm not found. Please install NodeJS from https://nodejs.org and retry.")
        return
    print_step("Installing web dependencies...")
    new_env = dict(env)
    new_env["VITE_BACKEND_URL"] = backend_url
    run([npm_exe, "install"], cwd=FRONTEND)
    print_step("Starting Vite dev server on :5173...")
    proc = run_bg([npm_exe, "run", "dev"], cwd=FRONTEND, env=new_env)
    time.sleep(2)
    webbrowser.open("http://localhost:5173")
    return proc


def open_docs():
    port = os.environ.get("PORT", "8000")
    url = f"http://localhost:{port}/docs"
    print_step(f"Opening API docs: {url}")
    webbrowser.open(url)


def start_all(start_web: bool = True) -> None:
    bootstrap()
    ensure_node()
    ensure_java()
    pull_models()
    env = ensure_env()
    chroma = start_chroma(env)
    backend, port = start_backend(env)
    # Record chosen port so open_docs() and others know
    try:
        os.environ["PORT"] = str(port)
    except Exception:
        pass
    # Respect flag and AUTO_WEB env (set AUTO_WEB=0 to skip)
    start_ui = start_web and os.getenv("AUTO_WEB", "1") != "0"
    web = None
    if start_ui:
        backend_url = f"http://localhost:{port}"
        web = start_frontend_dev(env, backend_url)
    open_docs()

    print_ok("All services started. Press Ctrl+C to stop.")
    procs = [p for p in [chroma, backend, web] if p is not None]
    try:
        # Wait until either process exits or Ctrl+C
        while any(p.poll() is None for p in procs):
            time.sleep(0.5)
    except KeyboardInterrupt:
        print_step("Stopping services...")
    finally:
        for p in procs:
            try:
                if p and p.poll() is None:
                    p.terminate()
            except Exception:
                pass
        time.sleep(0.8)
        for p in procs:
            try:
                if p and p.poll() is None:
                    p.kill()
            except Exception:
                pass
        print_ok("Stopped.")


def main():
    parser = argparse.ArgumentParser(description="Dev runner")
    sub = parser.add_subparsers(dest="cmd")
    p_start = sub.add_parser("start", help="Bootstrap and start all services + open frontend")
    p_start.add_argument("--no-web", action="store_true", help="Start backend only (skip web UI)")
    sub.add_parser("bootstrap", help="Create venv and install requirements")
    sub.add_parser("pull-models", help="Verify Ollama and pull required models")
    sub.add_parser("start-frontend", help="Start the Vite dev server for the web UI")
    sub.add_parser("check", help="Check system prerequisites")

    args = parser.parse_args()
    if args.cmd == "bootstrap":
        bootstrap()
        return
    if args.cmd == "pull-models":
        pull_models()
        return
    if args.cmd == "start-frontend":
        env = ensure_env()
        start_frontend_dev(env)
        return
    if args.cmd == "check":
        print_step("System check...")
        print_ok(f"Python: {sys.version}")
        ensure_node()
        ensure_java()
        print_ok("Check complete.")
        return
    # default to start
    start_all(start_web=not getattr(args, "no_web", False))


if __name__ == "__main__":
    main()

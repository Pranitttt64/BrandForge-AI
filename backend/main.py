import os
from dotenv import load_dotenv
load_dotenv()

import sys
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass

# --- Startup environment check ---
required_env = ["GROQ_API_KEY", "GEMINI_API_KEY"]
missing_env  = [k for k in required_env if not os.getenv(k)]
if missing_env:
    print(f"[WARN] Missing env vars: {missing_env}. Set them in backend/.env")

import asyncio
import json
from pathlib import Path
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, field_validator

from job_manager import job_manager, job_queues, run_pipeline_background

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="BrandForge AI",
    version="1.0.0",
    description="Autonomous brand intelligence and marketing asset generator.",
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

_raw_origins = os.getenv("FRONTEND_URL", "http://localhost:3000")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

# ---------------------------------------------------------------------------
# Startup — warm up embedding model so first request is fast
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def startup_event():
    print("[startup] BrandForge AI starting...")
    loop = asyncio.get_event_loop()
    try:
        from rag.embedder import warmup
        await loop.run_in_executor(None, warmup)
    except Exception as e:
        print(f"[startup] Embedding warmup failed (non-fatal): {e}")
    print("[startup] Ready.")

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class ForgeRequest(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("URL cannot be empty.")
        if not v.startswith(("http://", "https://")):
            v = "https://" + v
        # Basic sanity check
        if "." not in v.split("//")[-1].split("/")[0]:
            raise ValueError("URL does not look valid.")
        return v

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

import httpx

@app.post("/api/validate-url")
async def validate_url(req: ForgeRequest):
    """Real HTTP check to ensure the URL actually exists."""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            resp = await client.get(req.url)
            if resp.status_code >= 400:
                raise HTTPException(status_code=400, detail=f"URL returned status {resp.status_code}")
        return {"valid": True, "url": str(resp.url)}
    except Exception as e:
        raise HTTPException(status_code=400, detail="URL is unreachable. Please check the spelling.")

@app.post("/api/forge")
async def start_forge(req: ForgeRequest, background_tasks: BackgroundTasks):
    """
    Start a new BrandForge pipeline job.
    Returns job_id immediately; pipeline runs in background.
    """
    job_id = str(uuid4())[:8]
    job_manager.create_job(job_id)
    background_tasks.add_task(run_pipeline_background, job_id, req.url)
    print(f"[forge] Job started: {job_id} → {req.url}")
    return {"job_id": job_id, "status": "started"}


@app.get("/api/forge/{job_id}/stream")
async def stream_job(job_id: str):
    """
    SSE stream. Emits pipeline events until complete or error.
    Heartbeat ping every 10s prevents proxy/load-balancer timeouts.
    Ping lines (': ping') are NOT data events — frontend must ignore them.
    """
    if job_id not in job_queues:
        raise HTTPException(status_code=404, detail="Job not found or already expired.")

    queue = job_queues[job_id]

    async def event_generator():
        loop = asyncio.get_event_loop()
        last_ping = loop.time()

        try:
            while True:
                now = loop.time()

                # Heartbeat
                if now - last_ping >= 10:
                    yield ": ping\n\n"
                    last_ping = now

                try:
                    event = await asyncio.wait_for(queue.get(), timeout=2.0)
                    payload = json.dumps(event, ensure_ascii=False)
                    yield f"data: {payload}\n\n"

                    if event.get("type") in ("complete", "error"):
                        break

                except asyncio.TimeoutError:
                    continue

        except asyncio.CancelledError:
            pass  # Client disconnected

        finally:
            job_manager.cleanup(job_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Content-Type":      "text/event-stream",
            "Cache-Control":     "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection":        "keep-alive",
            "Access-Control-Allow-Origin": ALLOWED_ORIGINS[0] if ALLOWED_ORIGINS else "*",
        },
    )


@app.get("/api/forge/{job_id}/result")
async def get_result(job_id: str):
    """
    Returns the full pipeline result for a completed job.
    Returns 202 + {status: running} while still in progress.
    Returns 404 if job unknown.
    """
    # Still running
    if job_id in job_manager.jobs and job_id not in job_manager.results:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=202,
            content={"status": "running", "job_id": job_id},
        )

    # Not found at all
    if job_id not in job_manager.results:
        raise HTTPException(status_code=404, detail="Job not found.")

    state = job_manager.results[job_id]
    copy  = state.get("copy_output") or {}

    return {
        "status":          "complete",
        "job_id":          job_id,
        "brand_name":      state.get("brand_name", ""),
        "brand_tone":      state.get("brand_tone", ""),
        "brand_category":  state.get("brand_category", ""),
        "target_audience": state.get("target_audience", ""),
        "brand_promise":   state.get("brand_promise", ""),
        "usps":            state.get("usps", []),
        "tagline":         copy.get("tagline", ""),
        "elevator_pitch":  copy.get("elevator_pitch", ""),
        "brand_profile":   state.get("brand_profile", {}),
        "copy_output":     state.get("copy_output", {}),
        "email_output":    state.get("email_output", {}),
        "ad_output":       state.get("ad_output", {}),
        "layout_output":   state.get("layout_output", {}),
        "zip_path":        state.get("zip_path", ""),
        "scrape_status":   state.get("scrape_status", ""),
    }


@app.get("/api/forge/{job_id}/download")
async def download_result(job_id: str):
    """
    Download the brand kit ZIP.
    Returns 404 if job not complete or ZIP missing.
    """
    if job_id not in job_manager.results:
        raise HTTPException(
            status_code=404,
            detail="Result not found — job may still be running.",
        )

    state    = job_manager.results[job_id]
    zip_path = state.get("zip_path", "")

    if not zip_path or not Path(zip_path).exists():
        raise HTTPException(
            status_code=404,
            detail="ZIP file not found — asset generation may have failed.",
        )

    filename = Path(zip_path).name
    return FileResponse(
        path=str(zip_path),
        filename=filename,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/forge/{job_id}/assets/{filename}")
async def get_asset(job_id: str, filename: str):
    """
    Serve individual generated assets (flyer.pdf, social_card.png, etc.)
    for inline preview in the frontend.
    """
    # Safety: prevent path traversal
    safe_name = Path(filename).name
    asset_path = Path("outputs") / job_id / "assets" / safe_name

    if not asset_path.exists():
        raise HTTPException(status_code=404, detail=f"Asset not found: {safe_name}")

    # Determine media type
    suffix = asset_path.suffix.lower()
    media_types = {
        ".pdf":  "application/pdf",
        ".png":  "image/png",
        ".jpg":  "image/jpeg",
        ".jpeg": "image/jpeg",
        ".html": "text/html",
        ".json": "application/json",
        ".txt":  "text/plain",
        ".zip":  "application/zip",
    }
    media_type = media_types.get(suffix, "application/octet-stream")

    return FileResponse(
        path=str(asset_path),
        media_type=media_type,
        headers={"Cache-Control": "no-cache"},
    )


@app.get("/health")
async def health():
    """Health check endpoint for deployment monitoring."""
    return {
        "status":  "ok",
        "service": "BrandForge AI",
        "version": "1.0.0",
    }


# ---------------------------------------------------------------------------
# Entry point — local dev only
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=bool(os.getenv("DEV_RELOAD", "false").lower() == "true"),
        timeout_keep_alive=120,
    )
"""
Job Manager — BrandForge AI
Manages per-job asyncio queues for SSE streaming and stores final states.
"""

from __future__ import annotations

import asyncio
import traceback



class JobManager:
    def __init__(self):
        self.jobs:    dict[str, asyncio.Queue] = {}   # job_id → event queue
        self.results: dict[str, dict]          = {}   # job_id → final state

    def create_job(self, job_id: str) -> None:
        self.jobs[job_id] = asyncio.Queue()

    def emit(self, job_id: str, event: dict) -> None:
        """Non-blocking event push to the job's SSE queue."""
        if job_id in self.jobs:
            try:
                self.jobs[job_id].put_nowait(event)
            except asyncio.QueueFull:
                print(f"[job_manager] Queue full for job {job_id} — event dropped")
            except Exception as e:
                print(f"[job_manager] emit error for {job_id}: {e}")

    def get_queue(self, job_id: str) -> asyncio.Queue | None:
        return self.jobs.get(job_id)

    def cleanup(self, job_id: str) -> None:
        """Remove the SSE queue after the stream closes.
        Results are kept for the /result and /download endpoints.
        """
        if job_id in self.jobs:
            del self.jobs[job_id]
            print(f"[job_manager] Queue cleaned up for job {job_id}")


# Singleton — imported by main.py and all pipeline nodes
job_manager = JobManager()
job_queues  = job_manager.jobs   # direct reference for main.py backward compat


async def run_pipeline_background(job_id: str, url: str) -> None:
    """
    Runs the full LangGraph pipeline asynchronously.
    Emits SSE events throughout, stores final state on completion.
    Always emits a terminal event so the stream closes cleanly.
    """
    from pipeline.graph import create_pipeline_graph
    from pipeline.state import make_initial_state
    graph = create_pipeline_graph()

    try:
        job_manager.emit(job_id, {
            "type":    "init",
            "stage":   "init",
            "status":  "started",
            "message": f"Pipeline started for {url}",
            "url":     url,
        })

        initial_state = make_initial_state(url=url, job_id=job_id)
        final_state   = await graph.ainvoke(initial_state)

        # Store final state for /result and /download endpoints
        job_manager.results[job_id] = final_state

        download_url = f"/api/forge/{job_id}/download"
        brand_name   = final_state.get("brand_name", "")
        zip_path     = final_state.get("zip_path", "")

        print(
            f"[job_manager] Pipeline complete: {job_id} | "
            f"brand={brand_name} | zip={zip_path}"
        )

        job_manager.emit(job_id, {
            "type":         "complete",
            "stage":        "complete",
            "status":       "success",
            "message":      f"Brand kit ready for {brand_name}",
            "download_url": download_url,
            "brand_name":   brand_name,
            "zip_path":     zip_path,
        })

    except Exception as e:
        tb = traceback.format_exc()
        print(f"[job_manager] Pipeline failed for {job_id}:\n{tb}")

        job_manager.emit(job_id, {
            "type":    "error",
            "stage":   "error",
            "status":  "failed",
            "message": f"Pipeline error: {str(e)}",
        })

    finally:
        # Always send the terminal complete event so the SSE stream closes
        queue = job_manager.get_queue(job_id)
        if queue:
            await queue.put({
                "type":    "complete",
                "stage":   "complete",
                "status":  "complete",
                "message": "Stream closing",
            })
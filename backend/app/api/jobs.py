"""Job CRUD, SSE stream, content patch, rate, regenerate."""

from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator, Literal, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.pipeline.runner import regenerate_platform, run_full_pipeline
from app.store import get_store

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


class CreateJobBody(BaseModel):
    url: str = Field(..., min_length=10)


class PatchContentBody(BaseModel):
    platform: Literal["linkedin", "twitter"]
    content: Any  # str for linkedin, dict for twitter


class RateBody(BaseModel):
    platform: Literal["linkedin", "twitter"]
    score: int = Field(ge=1, le=5)
    notes: Optional[str] = None


class RegenerateBody(BaseModel):
    platform: Literal["linkedin", "twitter"]


@router.post("")
async def create_job(body: CreateJobBody, background_tasks: BackgroundTasks) -> dict[str, str]:
    store = get_store()
    job_id = store.create_job(body.url.strip())
    background_tasks.add_task(_schedule_pipeline_wrapped, job_id, body.url.strip())
    return {"job_id": job_id}


async def _schedule_pipeline_wrapped(job_id: str, url: str) -> None:
    await run_full_pipeline(job_id, url, get_store())


@router.get("/{job_id}")
async def get_job(job_id: str) -> dict[str, Any]:
    store = get_store()
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return store.get_job_response(job_id)


async def _sse_iter(job_id: str) -> AsyncIterator[bytes]:
    store = get_store()
    job = store.get_job(job_id)
    if not job:
        yield f"data: {json.dumps({'type': 'error', 'message': 'Job not found'})}\n\n".encode()
        return

    queue = store.event_queue(job_id)

    # Replay terminal state if already complete or error
    if job.get("status") == "complete":
        yield f"data: {json.dumps({'type': 'job.complete', 'job': store.get_job_response(job_id)})}\n\n".encode()
        return
    if job.get("status") == "error":
        yield f"data: {json.dumps({'type': 'step.error', 'step': 'pipeline', 'message': job.get('error_message')})}\n\n".encode()
        return

    while True:
        try:
            event = await asyncio.wait_for(queue.get(), timeout=300.0)
        except asyncio.TimeoutError:
            yield f"data: {json.dumps({'type': 'error', 'message': 'SSE timeout'})}\n\n".encode()
            break

        line = f"data: {json.dumps(event)}\n\n".encode()
        yield line
        if event.get("type") == "job.complete":
            break
        if event.get("type") == "step.error" and event.get("step") == "pipeline":
            break


@router.get("/{job_id}/stream")
async def stream_job(job_id: str) -> StreamingResponse:
    return StreamingResponse(
        _sse_iter(job_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.patch("/{job_id}/content")
async def patch_content(job_id: str, body: PatchContentBody) -> dict[str, Any]:
    store = get_store()
    try:
        store.require_job(job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Job not found")

    if body.platform == "linkedin":
        if not isinstance(body.content, str):
            raise HTTPException(status_code=400, detail="LinkedIn content must be a string")
        store.patch_job(job_id, linkedin_post=body.content)
    else:
        if not isinstance(body.content, dict):
            raise HTTPException(status_code=400, detail="Twitter content must be an object")
        store.patch_job(job_id, twitter_post=body.content)

    store.persist(job_id)
    return {"ok": True, "job": store.get_job_response(job_id)}


@router.post("/{job_id}/rate")
async def rate_job(job_id: str, body: RateBody) -> dict[str, Any]:
    store = get_store()
    try:
        job = store.require_job(job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Job not found")

    ratings = dict(job.get("ratings") or {})
    ratings[body.platform] = {"score": body.score, "notes": body.notes}
    store.patch_job(job_id, ratings=ratings)
    store.persist(job_id)
    return {"ok": True, "ratings": ratings}


@router.post("/{job_id}/regenerate")
async def regenerate_job(job_id: str, body: RegenerateBody) -> dict[str, Any]:
    store = get_store()
    try:
        store.require_job(job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Job not found")

    try:
        result = await regenerate_platform(job_id, body.platform, store)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"ok": True, **result, "job": store.get_job_response(job_id)}

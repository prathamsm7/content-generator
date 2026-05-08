"""Post CRUD, SSE stream, content patch, rate, regenerate."""

from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator, Literal, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.pipeline.runner import regenerate_platform, run_full_pipeline
from app.store import get_store

router = APIRouter(prefix="/api/posts", tags=["posts"])


class CreatePostBody(BaseModel):
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
async def create_post(body: CreatePostBody, background_tasks: BackgroundTasks) -> dict[str, str]:
    store = get_store()
    post_id = store.create_post(body.url.strip())
    background_tasks.add_task(_schedule_pipeline_wrapped, post_id, body.url.strip())
    return {"post_id": post_id}


async def _schedule_pipeline_wrapped(post_id: str, url: str) -> None:
    await run_full_pipeline(post_id, url, get_store())


@router.get("/{post_id}")
async def get_post(post_id: str) -> dict[str, Any]:
    store = get_store()
    post = store.get_post(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return store.get_post_response(post_id)


async def _sse_iter(post_id: str) -> AsyncIterator[bytes]:
    store = get_store()
    post = store.get_post(post_id)
    if not post:
        yield f"data: {json.dumps({'type': 'error', 'message': 'Post not found'})}\n\n".encode()
        return

    queue = store.event_queue(post_id)

    # Replay terminal state if already complete or error
    if post.get("status") == "complete":
        yield f"data: {json.dumps({'type': 'post.complete', 'post': store.get_post_response(post_id)})}\n\n".encode()
        return
    if post.get("status") == "error":
        yield f"data: {json.dumps({'type': 'step.error', 'step': 'pipeline', 'message': post.get('error_message')})}\n\n".encode()
        return

    while True:
        try:
            event = await asyncio.wait_for(queue.get(), timeout=300.0)
        except asyncio.TimeoutError:
            yield f"data: {json.dumps({'type': 'error', 'message': 'SSE timeout'})}\n\n".encode()
            break

        line = f"data: {json.dumps(event)}\n\n".encode()
        yield line
        if event.get("type") == "post.complete":
            break
        if event.get("type") == "step.error" and event.get("step") == "pipeline":
            break


@router.get("/{post_id}/stream")
async def stream_post(post_id: str) -> StreamingResponse:
    return StreamingResponse(
        _sse_iter(post_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.patch("/{post_id}/content")
async def patch_content(post_id: str, body: PatchContentBody) -> dict[str, Any]:
    store = get_store()
    try:
        store.require_post(post_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Post not found")

    if body.platform == "linkedin":
        if not isinstance(body.content, str):
            raise HTTPException(status_code=400, detail="LinkedIn content must be a string")
        store.patch_post(post_id, linkedin_post=body.content)
    else:
        if not isinstance(body.content, dict):
            raise HTTPException(status_code=400, detail="Twitter content must be an object")
        store.patch_post(post_id, twitter_post=body.content)

    store.persist(post_id)
    return {"ok": True, "post": store.get_post_response(post_id)}


@router.post("/{post_id}/rate")
async def rate_post(post_id: str, body: RateBody) -> dict[str, Any]:
    store = get_store()
    try:
        post = store.require_post(post_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Post not found")

    ratings = dict(post.get("ratings") or {})
    ratings[body.platform] = {"score": body.score, "notes": body.notes}
    store.patch_post(post_id, ratings=ratings)
    store.persist(post_id)
    return {"ok": True, "ratings": ratings}


@router.post("/{post_id}/regenerate")
async def regenerate_post(post_id: str, body: RegenerateBody) -> dict[str, Any]:
    store = get_store()
    try:
        store.require_post(post_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Post not found")

    try:
        result = await regenerate_platform(post_id, body.platform, store)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"ok": True, **result, "post": store.get_post_response(post_id)}

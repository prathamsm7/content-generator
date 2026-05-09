"""Post CRUD, SSE stream, content patch, rate, regenerate."""

from __future__ import annotations

import asyncio
import json
from typing import Annotated, Any, AsyncIterator, Literal, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.auth import get_current_user, get_current_user_from_query
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
    feedback: Optional[str] = Field(default=None, max_length=500)


@router.post("")
async def create_post(
    body: CreatePostBody,
    background_tasks: BackgroundTasks,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict[str, str]:
    store = get_store()
    post_id = store.create_post(body.url.strip(), current_user["user_id"])
    background_tasks.add_task(_schedule_pipeline_wrapped, post_id, body.url.strip())
    return {"post_id": post_id}


async def _schedule_pipeline_wrapped(post_id: str, url: str) -> None:
    await run_full_pipeline(post_id, url, get_store())


@router.get("")
async def list_posts(current_user: Annotated[dict, Depends(get_current_user)]) -> dict[str, Any]:
    return {"posts": get_store().list_posts(current_user["user_id"])}


@router.get("/{post_id}")
async def get_post(
    post_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict[str, Any]:
    store = get_store()
    post = store.get_post(post_id, current_user["user_id"])
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return store.get_post_response(post_id, current_user["user_id"])


async def _sse_iter(post_id: str, user_id: str) -> AsyncIterator[bytes]:
    store = get_store()
    post = store.get_post(post_id, user_id)
    if not post:
        yield f"data: {json.dumps({'type': 'error', 'message': 'Post not found'})}\n\n".encode()
        return

    queue = store.event_queue(post_id)

    # Replay terminal state if already complete or error
    if post.get("status") == "complete":
        yield f"data: {json.dumps({'type': 'post.complete', 'post': store.get_post_response(post_id, user_id)})}\n\n".encode()
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
async def stream_post(
    post_id: str,
    current_user: Annotated[dict, Depends(get_current_user_from_query)],
) -> StreamingResponse:
    return StreamingResponse(
        _sse_iter(post_id, current_user["user_id"]),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.patch("/{post_id}/content")
async def patch_content(
    post_id: str,
    body: PatchContentBody,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict[str, Any]:
    store = get_store()
    try:
        store.require_post(post_id, current_user["user_id"])
    except KeyError:
        raise HTTPException(status_code=404, detail="Post not found")

    if body.platform == "linkedin":
        if not isinstance(body.content, str):
            raise HTTPException(status_code=400, detail="LinkedIn content must be a string")
        updated_content = store.set_platform_content(post_id, "linkedin", body.content, source="edited")
    else:
        if not isinstance(body.content, dict):
            raise HTTPException(status_code=400, detail="Twitter content must be an object")
        updated_content = store.set_platform_content(post_id, "twitter", body.content, source="edited")

    store.persist(post_id)
    return {"ok": True, **updated_content}


@router.post("/{post_id}/rate")
async def rate_post(
    post_id: str,
    body: RateBody,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict[str, Any]:
    store = get_store()
    try:
        store.require_post(post_id, current_user["user_id"])
    except KeyError:
        raise HTTPException(status_code=404, detail="Post not found")

    ratings = store.rate_active_content(
        post_id=post_id,
        platform=body.platform,
        user_id=current_user["user_id"],
        score=body.score,
        notes=body.notes,
    )
    store.persist(post_id)
    return {"ok": True, "ratings": ratings}


@router.post("/{post_id}/regenerate")
async def regenerate_post(
    post_id: str,
    body: RegenerateBody,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict[str, Any]:
    store = get_store()
    try:
        store.require_post(post_id, current_user["user_id"])
    except KeyError:
        raise HTTPException(status_code=404, detail="Post not found")

    try:
        result = await regenerate_platform(post_id, body.platform, store, body.feedback)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"ok": True, **result}

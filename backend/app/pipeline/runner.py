"""Run the content generation pipeline and send progress events to the frontend.

This file is intentionally written in a beginner-friendly style.

High-level flow:
1. Extract video id from the YouTube URL.
2. Fetch transcript.
3. Execute the compiled LangGraph.
4. Listen to graph node updates.
5. Save node outputs and notify the frontend.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any

from app.pipeline.graph import build_compiled_graph
from app.pipeline.nodes import linkedin_post_node, twitter_post_node
from app.pipeline.schemas import VideoContext
from app.store import PostStore


YOUTUBE_VIDEO_ID_PATTERN = re.compile(
    r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/|youtube\.com/shorts/)([\w-]{11})"
)


def extract_video_id(url: str) -> str:
    """Extract the 11-character YouTube video id from common YouTube URL formats."""
    cleaned_url = url.strip()

    youtube_url_match = YOUTUBE_VIDEO_ID_PATTERN.search(cleaned_url)
    if youtube_url_match:
        return youtube_url_match.group(1)

    # Fallback: if the user somehow submits only the video id, accept it.
    raw_video_id_match = re.search(r"[\w-]{11}", cleaned_url)
    if raw_video_id_match:
        return raw_video_id_match.group(0)

    raise ValueError("Could not parse a valid YouTube video ID from the URL.")


def _build_pipeline_state_for_regeneration(saved_post: dict[str, Any]) -> dict[str, Any]:
    """Recreate the minimum pipeline state needed to regenerate a post.

    Regeneration does not fetch transcript or metadata again.
    It reuses already saved transcript + video analysis.
    """
    raw_video_context = saved_post.get("video_context") or {}
    video_context = (
        VideoContext(**raw_video_context)
        if isinstance(raw_video_context, dict)
        else raw_video_context
    )

    return {
        "video_id": saved_post["video_id"],
        "transcript": saved_post["transcript"],
        "title": saved_post.get("title") or "",
        "tags": saved_post.get("tags") or [],
        "video_context": video_context,
    }


def _update_step_status(
    post_store: PostStore,
    post_id: str,
    step_name: str,
    step_status: str,
) -> None:
    """Update one step's status in the persisted post record."""
    saved_post = post_store.require_post(post_id)
    all_step_statuses = dict(saved_post.get("step_status") or {})
    all_step_statuses[step_name] = step_status
    post_store.patch_post(post_id, step_status=all_step_statuses)


def _serialize_pydantic_model(value: Any) -> Any:
    """Convert Pydantic models to dictionaries before saving as JSON."""
    return value.model_dump() if hasattr(value, "model_dump") else value


async def _emit_event(
    event_queue: asyncio.Queue[dict[str, Any]],
    event_payload: dict[str, Any],
) -> None:
    """Send one event to the frontend through the post's SSE queue."""
    await event_queue.put(event_payload)


async def _mark_step_as_started(
    post_store: PostStore,
    post_id: str,
    event_queue: asyncio.Queue[dict[str, Any]],
    step_name: str,
) -> None:
    """Tell the frontend and storage that a pipeline step has started."""
    await _emit_event(event_queue, {"type": "step.start", "step": step_name})
    _update_step_status(post_store, post_id, step_name, "running")
    post_store.persist(post_id)


async def _mark_step_as_completed(
    post_store: PostStore,
    post_id: str,
    event_queue: asyncio.Queue[dict[str, Any]],
    step_name: str,
    output_preview: str = "",
) -> None:
    """Tell the frontend and storage that a pipeline step has finished."""
    await _emit_event(
        event_queue,
        {
            "type": "step.complete",
            "step": step_name,
            "output_preview": output_preview,
        },
    )
    _update_step_status(post_store, post_id, step_name, "complete")
    post_store.persist(post_id)


def _extract_node_update_from_graph_chunk(
    graph_chunk: Any,
) -> tuple[str | None, dict[str, Any]]:
    """Read one LangGraph stream chunk.

    With stream_mode="updates", LangGraph usually yields data like:

        {"transcription": {"transcript": "..."}}

    The dictionary key is the node name.
    The inner dictionary is what that node returned.
    """
    if not isinstance(graph_chunk, dict):
        return None, {}

    if len(graph_chunk) == 1:
        node_name = next(iter(graph_chunk.keys()))
        node_output = graph_chunk[node_name]
        if isinstance(node_output, dict):
            return node_name, node_output

    return None, graph_chunk


def _merge_node_output_into_pipeline_state(
    pipeline_state: dict[str, Any],
    node_output: dict[str, Any],
) -> None:
    """Keep a local copy of the latest graph state.

    LangGraph owns the real execution state internally.
    This local copy is only used so we can save values to the post store.
    """
    pipeline_state.update(node_output)


async def _handle_transcription_update(
    post_id: str,
    post_store: PostStore,
    event_queue: asyncio.Queue[dict[str, Any]],
    pipeline_state: dict[str, Any],
) -> None:
    transcript_text = pipeline_state.get("transcript") or ""
    transcript_preview = transcript_text[:240]

    await _mark_step_as_completed(
        post_store,
        post_id,
        event_queue,
        "transcription",
        transcript_preview,
    )
    post_store.patch_post(post_id, transcript=transcript_text)
    post_store.persist(post_id)


def _handle_metadata_update(
    post_id: str,
    post_store: PostStore,
    pipeline_state: dict[str, Any],
) -> None:
    """Save metadata as soon as the video_metadata node finishes.

    We do not mark the frontend metadata step complete yet.
    The frontend metadata step represents both metadata + analysis.
    It completes after video_context finishes.
    """
    post_store.patch_post(
        post_id,
        title=pipeline_state.get("title") or "",
        tags=pipeline_state.get("tags") or [],
    )
    post_store.persist(post_id)


async def _handle_video_context_update(
    post_id: str,
    post_store: PostStore,
    event_queue: asyncio.Queue[dict[str, Any]],
    pipeline_state: dict[str, Any],
    started_steps: set[str],
) -> None:
    video_context = pipeline_state["video_context"]
    video_title = pipeline_state.get("title") or ""
    video_tone = getattr(video_context, "tone", "")
    metadata_preview = f"{video_title[:100]} | {video_tone}"

    await _mark_step_as_completed(
        post_store,
        post_id,
        event_queue,
        "metadata",
        metadata_preview,
    )
    post_store.patch_post(
        post_id,
        video_context=_serialize_pydantic_model(video_context),
    )
    post_store.persist(post_id)

    # After analysis is done, LangGraph will fan out into platform generation.
    # Mark both platform steps as started for the loading UI.
    for platform_step in ("linkedin", "twitter"):
        if platform_step not in started_steps:
            await _mark_step_as_started(post_store, post_id, event_queue, platform_step)
            started_steps.add(platform_step)


async def _handle_linkedin_update(
    post_id: str,
    post_store: PostStore,
    event_queue: asyncio.Queue[dict[str, Any]],
    pipeline_state: dict[str, Any],
    started_steps: set[str],
) -> None:
    if "linkedin" not in started_steps:
        await _mark_step_as_started(post_store, post_id, event_queue, "linkedin")
        started_steps.add("linkedin")

    linkedin_post_text = pipeline_state.get("linkedin_post") or ""
    linkedin_preview = linkedin_post_text[:160]

    await _mark_step_as_completed(
        post_store,
        post_id,
        event_queue,
        "linkedin",
        linkedin_preview,
    )
    post_store.patch_post(post_id, linkedin_post=linkedin_post_text)
    post_store.persist(post_id)


async def _handle_twitter_update(
    post_id: str,
    post_store: PostStore,
    event_queue: asyncio.Queue[dict[str, Any]],
    pipeline_state: dict[str, Any],
    started_steps: set[str],
) -> None:
    if "twitter" not in started_steps:
        await _mark_step_as_started(post_store, post_id, event_queue, "twitter")
        started_steps.add("twitter")

    twitter_post_model = pipeline_state["twitter_post"]
    twitter_post_dict = _serialize_pydantic_model(twitter_post_model)
    best_single_tweet = twitter_post_dict.get("best_single_tweet") or {}
    twitter_preview = (best_single_tweet.get("text") or "")[:160]

    await _mark_step_as_completed(
        post_store,
        post_id,
        event_queue,
        "twitter",
        twitter_preview,
    )
    post_store.patch_post(post_id, twitter_post=twitter_post_dict)
    post_store.persist(post_id)


async def _handle_graph_update(
    post_id: str,
    post_store: PostStore,
    event_queue: asyncio.Queue[dict[str, Any]],
    pipeline_state: dict[str, Any],
    started_steps: set[str],
    graph_chunk: Any,
) -> None:
    """Convert one LangGraph update into post persistence + frontend SSE events."""
    node_name, node_output = _extract_node_update_from_graph_chunk(graph_chunk)
    _merge_node_output_into_pipeline_state(pipeline_state, node_output)

    if node_name == "transcription":
        await _handle_transcription_update(post_id, post_store, event_queue, pipeline_state)
    elif node_name == "video_metadata":
        _handle_metadata_update(post_id, post_store, pipeline_state)
    elif node_name == "video_context":
        await _handle_video_context_update(
            post_id,
            post_store,
            event_queue,
            pipeline_state,
            started_steps,
        )
    elif node_name == "linkedin_post":
        await _handle_linkedin_update(
            post_id,
            post_store,
            event_queue,
            pipeline_state,
            started_steps,
        )
    elif node_name == "twitter_post":
        await _handle_twitter_update(
            post_id,
            post_store,
            event_queue,
            pipeline_state,
            started_steps,
        )


async def run_full_pipeline(post_id: str, url: str, store: PostStore) -> None:
    """Run the full YouTube -> transcript -> analysis -> content generation flow.

    Important:
    The actual orchestration is done by LangGraph.
    This runner only:
    - starts the graph
    - listens to graph node updates
    - saves outputs
    - sends progress events to the frontend
    """
    event_queue = store.event_queue(post_id)

    try:
        video_id = extract_video_id(url)
        store.patch_post(post_id, video_id=video_id, status="running", error_message=None)

        # This is the initial graph state.
        # LangGraph will pass this state through all graph nodes.
        pipeline_state: dict[str, Any] = {"video_id": video_id}

        # These two graph branches start from START and can run independently.
        started_steps = {"transcription", "metadata"}
        await _mark_step_as_started(store, post_id, event_queue, "transcription")
        await _mark_step_as_started(store, post_id, event_queue, "metadata")

        compiled_graph = build_compiled_graph()

        # stream_mode="updates" yields each node's output as soon as it completes.
        # Example chunk:
        # {"transcription": {"transcript": "..."}}
        async for graph_update in compiled_graph.astream(
            pipeline_state,
            stream_mode="updates",
        ):
            await _handle_graph_update(
                post_id=post_id,
                post_store=store,
                event_queue=event_queue,
                pipeline_state=pipeline_state,
                started_steps=started_steps,
                graph_chunk=graph_update,
            )

        store.patch_post(post_id, status="complete")
        store.persist(post_id)

        await _emit_event(
            event_queue,
            {"type": "post.complete", "post": store.get_post_response(post_id)},
        )
    except Exception as error:
        await _emit_event(
            event_queue,
            {"type": "step.error", "step": "pipeline", "message": str(error)},
        )
        store.patch_post(post_id, status="error", error_message=str(error))
        store.persist(post_id)


async def regenerate_platform(post_id: str, platform: str, store: PostStore) -> dict[str, Any]:
    """Regenerate only one platform's content using the saved transcript + analysis."""
    saved_post = store.require_post(post_id)
    if not saved_post.get("transcript") or not saved_post.get("video_context"):
        raise ValueError("Post is missing transcript or analysis; run full pipeline first.")

    pipeline_state = _build_pipeline_state_for_regeneration(saved_post)

    if platform == "linkedin":
        linkedin_result = await asyncio.to_thread(linkedin_post_node, pipeline_state)
        linkedin_post_text = linkedin_result.get("linkedin_post", "")
        store.patch_post(post_id, linkedin_post=linkedin_post_text)
        store.persist(post_id)
        return {"platform": "linkedin", "content": linkedin_post_text}

    if platform == "twitter":
        twitter_result = await asyncio.to_thread(twitter_post_node, pipeline_state)
        twitter_post_model = twitter_result.get("twitter_post")
        twitter_post_dict = _serialize_pydantic_model(twitter_post_model)
        store.patch_post(post_id, twitter_post=twitter_post_dict)
        store.persist(post_id)
        return {"platform": "twitter", "content": twitter_post_dict}

    raise ValueError("platform must be 'linkedin' or 'twitter'")

"""LangGraph definition for the Repurposely content pipeline.

Graph flow:

START
  ├── transcription
  └── video_metadata
        ↓
video_context
  ├── linkedin_post
  └── twitter_post
        ↓
END

`video_context` needs both transcript and metadata, so the graph uses a
joining edge:

    graph.add_edge(["transcription", "video_metadata"], "video_context")

That tells LangGraph: run `video_context` only after both upstream nodes finish.
"""

from typing import List, TypedDict

from langgraph.graph import END, START, StateGraph

from app.pipeline.nodes import (
    linkedin_post_node,
    metadata_node,
    transcription_node,
    twitter_post_node,
    video_context_node,
)
from app.pipeline.schemas import VideoContext


class ContentState(TypedDict, total=False):
    video_id: str
    transcript: str
    title: str
    tags: List[str]
    video_context: VideoContext
    linkedin_post: str
    twitter_post: object


def build_compiled_graph():
    graph = StateGraph(ContentState)

    graph.add_node("transcription", transcription_node)
    graph.add_node("video_metadata", metadata_node)
    graph.add_node("video_context", video_context_node)
    graph.add_node("linkedin_post", linkedin_post_node)
    graph.add_node("twitter_post", twitter_post_node)

    # These two can run in parallel because they only need the video_id.
    graph.add_edge(START, "transcription")
    graph.add_edge(START, "video_metadata")

    # Wait for BOTH transcript and metadata before analyzing the video context.
    graph.add_edge(["transcription", "video_metadata"], "video_context")

    # Once the video is analyzed, generate platform-specific content in parallel.
    graph.add_edge("video_context", "linkedin_post")
    graph.add_edge("video_context", "twitter_post")

    # The graph should finish after BOTH platform writers are done.
    graph.add_edge(["linkedin_post", "twitter_post"], END)

    return graph.compile()

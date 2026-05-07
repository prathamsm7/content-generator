from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field


class VideoContext(BaseModel):
    tone: str
    audience: List[str]
    key_takeaways: List[str]
    category: List[str]
    intent: str


class SingleTweet(BaseModel):
    text: str
    selection_reason: str


class ThreadTweet(BaseModel):
    tweets: List[str]
    selection_reason: str


class TwitterPost(BaseModel):
    best_single_tweet: SingleTweet
    best_thread: ThreadTweet


class JobRating(BaseModel):
    platform: Literal["linkedin", "twitter"]
    score: int = Field(ge=1, le=5)
    notes: Optional[str] = None


class JobRecord(BaseModel):
    job_id: str
    url: str
    video_id: str
    status: Literal["pending", "running", "complete", "error"] = "pending"
    error_message: Optional[str] = None
    transcript: str = ""
    title: str = ""
    tags: List[str] = Field(default_factory=list)
    video_context: Optional[dict[str, Any]] = None
    linkedin_post: str = ""
    twitter_post: Optional[dict[str, Any]] = None
    ratings: dict[str, Any] = Field(default_factory=dict)  # platform -> {score, notes}

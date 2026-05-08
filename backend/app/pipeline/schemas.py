from typing import List

from pydantic import BaseModel


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

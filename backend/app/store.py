"""Database-backed app store plus in-memory SSE queues.

Permanent data lives in PostgreSQL/SQLite and is managed by Alembic migrations.
Live progress events stay in memory because they are temporary.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any, Optional

from app.db import SessionLocal
from app.models import (
    ContentRatingModel,
    PostContentModel,
    PostContentVersionModel,
    PostModel,
    PostTranscriptModel,
    UserModel,
    now_utc,
)
from sqlalchemy import select
from sqlalchemy.orm import Session


DEFAULT_STEP_STATUS = {
    "transcription": "idle",
    "metadata": "idle",
    "linkedin": "idle",
    "twitter": "idle",
}


class PostStore:
    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue[dict[str, Any]]] = {}

    def event_queue(self, post_id: str) -> asyncio.Queue[dict[str, Any]]:
        if post_id not in self._queues:
            self._queues[post_id] = asyncio.Queue()
        return self._queues[post_id]

    def create_user(self, email: str, password_hash: str, display_name: str = "") -> dict[str, Any]:
        user_id = str(uuid.uuid4())
        with self._session() as session:
            user = UserModel(
                id=user_id,
                email=email.lower(),
                password_hash=password_hash,
                display_name=display_name,
            )
            session.add(user)
            session.flush()
            return self._user_to_dict(user)

    def get_user(self, user_id: str) -> Optional[dict[str, Any]]:
        with self._session() as session:
            user = session.get(UserModel, user_id)
            return self._user_to_dict(user) if user else None

    def get_user_by_email(self, email: str) -> Optional[dict[str, Any]]:
        with self._session() as session:
            user = session.scalar(select(UserModel).where(UserModel.email == email.lower()))
            return self._user_to_dict(user) if user else None

    def create_post(self, url: str, user_id: str) -> str:
        post_id = str(uuid.uuid4())
        with self._session() as session:
            session.add(
                PostModel(
                    id=post_id,
                    user_id=user_id,
                    url=url,
                    step_status=dict(DEFAULT_STEP_STATUS),
                )
            )
        self.event_queue(post_id)
        return post_id

    def list_posts(self, user_id: str) -> list[dict[str, Any]]:
        with self._session() as session:
            posts = session.scalars(
                select(PostModel)
                .where(PostModel.user_id == user_id)
                .order_by(PostModel.created_at.desc())
            ).all()
            return [self._post_summary(session, post) for post in posts]

    def get_post(self, post_id: str, user_id: Optional[str] = None) -> Optional[dict[str, Any]]:
        with self._session() as session:
            post = session.get(PostModel, post_id)
            if not post or (user_id is not None and post.user_id != user_id):
                return None
            return self._to_dict(post) if post else None

    def require_post(self, post_id: str, user_id: Optional[str] = None) -> dict[str, Any]:
        post = self.get_post(post_id, user_id)
        if not post:
            raise KeyError("post_not_found")
        return post

    def patch_post(self, post_id: str, **kwargs: Any) -> None:
        with self._session() as session:
            post = session.get(PostModel, post_id)
            if not post:
                raise KeyError("post_not_found")

            for field_name, value in kwargs.items():
                if value is not None or field_name in ("error_message", "twitter_post", "video_context"):
                    setattr(post, field_name, value)

            post.updated_at = now_utc()

    def set_transcript(self, post_id: str, transcript_text: str) -> None:
        with self._session() as session:
            post = session.get(PostModel, post_id)
            if not post:
                raise KeyError("post_not_found")

            transcript = session.get(PostTranscriptModel, post_id)
            if not transcript:
                transcript = PostTranscriptModel(post_id=post_id)
                session.add(transcript)

            transcript.transcript_text = transcript_text
            transcript.char_count = len(transcript_text)
            transcript.updated_at = now_utc()
            post.updated_at = now_utc()

    def set_platform_content(
        self,
        post_id: str,
        platform: str,
        body: Any,
        source: str = "generated",
        feedback: Optional[str] = None,
    ) -> dict[str, Any]:
        with self._session() as session:
            post = session.get(PostModel, post_id)
            if not post:
                raise KeyError("post_not_found")

            content = session.scalar(
                select(PostContentModel).where(
                    PostContentModel.post_id == post_id,
                    PostContentModel.platform == platform,
                )
            )
            if not content:
                content = PostContentModel(id=str(uuid.uuid4()), post_id=post_id, platform=platform)
                session.add(content)
                session.flush()

            next_version = content.active_version_number + 1
            session.add(
                PostContentVersionModel(
                    id=str(uuid.uuid4()),
                    content_id=content.id,
                    version_number=next_version,
                    body=body,
                    source=source,
                    feedback=feedback,
                )
            )
            content.active_version_number = next_version
            content.updated_at = now_utc()
            post.updated_at = now_utc()
            return {
                "platform": platform,
                "content": body,
                "version_number": next_version,
                "source": source,
                "feedback": feedback,
            }

    def rate_active_content(
        self,
        post_id: str,
        platform: str,
        user_id: str,
        score: int,
        notes: Optional[str] = None,
    ) -> dict[str, Any]:
        with self._session() as session:
            active_version = self._active_version(session, post_id, platform)
            if not active_version:
                raise KeyError("content_not_found")

            rating = session.scalar(
                select(ContentRatingModel).where(
                    ContentRatingModel.content_version_id == active_version.id,
                    ContentRatingModel.user_id == user_id,
                )
            )
            if not rating:
                rating = ContentRatingModel(
                    id=str(uuid.uuid4()),
                    content_version_id=active_version.id,
                    user_id=user_id,
                    score=score,
                    notes=notes,
                )
                session.add(rating)
            else:
                rating.score = score
                rating.notes = notes
                rating.updated_at = now_utc()

            return self._ratings_for_post(session, post_id, user_id)

    def get_content_history(self, post_id: str, platform: str) -> list[dict[str, Any]]:
        with self._session() as session:
            content = session.scalar(
                select(PostContentModel).where(
                    PostContentModel.post_id == post_id,
                    PostContentModel.platform == platform,
                )
            )
            if not content:
                return []

            versions = session.scalars(
                select(PostContentVersionModel)
                .where(PostContentVersionModel.content_id == content.id)
                .order_by(PostContentVersionModel.version_number.desc())
            ).all()
            return [
                {
                    "version_number": version.version_number,
                    "body": version.body,
                    "source": version.source,
                    "feedback": version.feedback,
                    "created_at": version.created_at.isoformat() if version.created_at else None,
                }
                for version in versions
            ]

    def persist(self, post_id: str) -> None:
        # Kept for runner readability. SQLAlchemy commits inside each store method.
        self.require_post(post_id)

    def get_post_response(self, post_id: str, user_id: Optional[str] = None) -> dict[str, Any]:
        post = self.require_post(post_id, user_id)
        return {
            "post_id": post["post_id"],
            "status": post["status"],
            "error_message": post.get("error_message"),
            "linkedin_post": post.get("linkedin_post"),
            "twitter_post": post.get("twitter_post"),
            "ratings": post.get("ratings") or {},
            "step_status": post.get("step_status") or dict(DEFAULT_STEP_STATUS),
        }

    def _session(self) -> Session:
        return SessionLocal.begin()

    def _user_to_dict(self, user: UserModel) -> dict[str, Any]:
        return {
            "user_id": user.id,
            "email": user.email,
            "display_name": user.display_name,
            "password_hash": user.password_hash,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        }

    def _post_summary(self, session: Session, post: PostModel) -> dict[str, Any]:
        return {
            "post_id": post.id,
            "url": post.url,
            "title": post.title,
            "status": post.status,
            "created_at": post.created_at.isoformat() if post.created_at else None,
            "platforms": self._platforms_for_post(session, post.id),
        }

    def _to_dict(self, post: PostModel) -> dict[str, Any]:
        with SessionLocal() as session:
            transcript = session.get(PostTranscriptModel, post.id)
            linkedin_post = self._active_body(session, post.id, "linkedin") or ""
            twitter_post = self._active_body(session, post.id, "twitter")
            ratings = self._ratings_for_post(session, post.id, post.user_id)

        return {
            "post_id": post.id,
            "user_id": post.user_id,
            "url": post.url,
            "video_id": post.video_id,
            "status": post.status,
            "error_message": post.error_message,
            "transcript": transcript.transcript_text if transcript else "",
            "title": post.title,
            "tags": post.tags or [],
            "video_context": post.video_context,
            "linkedin_post": linkedin_post,
            "twitter_post": twitter_post,
            "ratings": ratings,
            "step_status": post.step_status or dict(DEFAULT_STEP_STATUS),
            "created_at": post.created_at.isoformat() if post.created_at else None,
            "updated_at": post.updated_at.isoformat() if post.updated_at else None,
        }

    def _platforms_for_post(self, session: Session, post_id: str) -> list[str]:
        return list(
            session.scalars(
                select(PostContentModel.platform)
                .where(PostContentModel.post_id == post_id)
                .order_by(PostContentModel.platform)
            ).all()
        )

    def _active_body(self, session: Session, post_id: str, platform: str) -> Any:
        active_version = self._active_version(session, post_id, platform)
        return active_version.body if active_version else None

    def _active_version(
        self,
        session: Session,
        post_id: str,
        platform: str,
    ) -> Optional[PostContentVersionModel]:
        content = session.scalar(
            select(PostContentModel).where(
                PostContentModel.post_id == post_id,
                PostContentModel.platform == platform,
            )
        )
        if not content or content.active_version_number == 0:
            return None

        return session.scalar(
            select(PostContentVersionModel).where(
                PostContentVersionModel.content_id == content.id,
                PostContentVersionModel.version_number == content.active_version_number,
            )
        )

    def _ratings_for_post(self, session: Session, post_id: str, user_id: str) -> dict[str, Any]:
        ratings: dict[str, Any] = {}
        contents = session.scalars(select(PostContentModel).where(PostContentModel.post_id == post_id)).all()
        for content in contents:
            active_version = self._active_version(session, post_id, content.platform)
            if not active_version:
                continue
            rating = session.scalar(
                select(ContentRatingModel).where(
                    ContentRatingModel.content_version_id == active_version.id,
                    ContentRatingModel.user_id == user_id,
                )
            )
            if rating:
                ratings[content.platform] = {"score": rating.score, "notes": rating.notes}
        return ratings


_store: Optional[PostStore] = None


def get_store() -> PostStore:
    global _store
    if _store is None:
        _store = PostStore()
    return _store

"""Database-backed post store plus in-memory SSE queues.

Permanent data lives in PostgreSQL (Neon in production).
Live progress events stay in memory because they are temporary.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from app.settings import get_settings
from sqlalchemy import JSON, DateTime, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


DEFAULT_STEP_STATUS = {
    "transcription": "idle",
    "metadata": "idle",
    "linkedin": "idle",
    "twitter": "idle",
}


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _normalize_database_url(database_url: str) -> str:
    """Make Neon/Postgres URLs work with the installed psycopg driver."""
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+psycopg://", 1)
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url


class Base(DeclarativeBase):
    pass


class PostModel(Base):
    __tablename__ = "posts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    video_id: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    transcript: Mapped[str] = mapped_column(Text, default="", nullable=False)
    title: Mapped[str] = mapped_column(Text, default="", nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    video_context: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)

    linkedin_post: Mapped[str] = mapped_column(Text, default="", nullable=False)
    twitter_post: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    ratings: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    step_status: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=lambda: dict(DEFAULT_STEP_STATUS),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc)


class PostStore:
    def __init__(self) -> None:
        settings = get_settings()
        database_url = _normalize_database_url(settings.database_url)

        if database_url.startswith("sqlite:///"):
            sqlite_path = database_url.replace("sqlite:///", "", 1)
            sqlite_file = Path(sqlite_path)
            if not sqlite_file.is_absolute():
                sqlite_file = _repo_root() / sqlite_file
            sqlite_file.parent.mkdir(parents=True, exist_ok=True)
            database_url = f"sqlite:///{sqlite_file}"

        connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
        self._engine = create_engine(database_url, connect_args=connect_args)
        self._session_factory = sessionmaker(self._engine, expire_on_commit=False)
        self._queues: dict[str, asyncio.Queue[dict[str, Any]]] = {}

        # Minimal setup for now. In a mature production app, replace this with Alembic migrations.
        Base.metadata.create_all(self._engine)

    def event_queue(self, post_id: str) -> asyncio.Queue[dict[str, Any]]:
        if post_id not in self._queues:
            self._queues[post_id] = asyncio.Queue()
        return self._queues[post_id]

    def create_post(self, url: str) -> str:
        post_id = str(uuid.uuid4())
        with self._session() as session:
            session.add(
                PostModel(
                    id=post_id,
                    url=url,
                    step_status=dict(DEFAULT_STEP_STATUS),
                )
            )
        self.event_queue(post_id)
        return post_id

    def get_post(self, post_id: str) -> Optional[dict[str, Any]]:
        with self._session() as session:
            post = session.get(PostModel, post_id)
            return self._to_dict(post) if post else None

    def require_post(self, post_id: str) -> dict[str, Any]:
        post = self.get_post(post_id)
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

            post.updated_at = _now_utc()

    def persist(self, post_id: str) -> None:
        # Kept for runner readability. SQLAlchemy commits inside each store method.
        self.require_post(post_id)

    def get_post_response(self, post_id: str) -> dict[str, Any]:
        post = self.require_post(post_id)
        return {
            "post_id": post["post_id"],
            "url": post["url"],
            "video_id": post["video_id"],
            "status": post["status"],
            "error_message": post.get("error_message"),
            "title": post.get("title"),
            "tags": post.get("tags"),
            "video_context": post.get("video_context"),
            "linkedin_post": post.get("linkedin_post"),
            "twitter_post": post.get("twitter_post"),
            "ratings": post.get("ratings") or {},
            "step_status": post.get("step_status") or dict(DEFAULT_STEP_STATUS),
        }

    def _session(self) -> Session:
        return self._session_factory.begin()

    def _to_dict(self, post: PostModel) -> dict[str, Any]:
        return {
            "post_id": post.id,
            "url": post.url,
            "video_id": post.video_id,
            "status": post.status,
            "error_message": post.error_message,
            "transcript": post.transcript,
            "title": post.title,
            "tags": post.tags or [],
            "video_context": post.video_context,
            "linkedin_post": post.linkedin_post,
            "twitter_post": post.twitter_post,
            "ratings": post.ratings or {},
            "step_status": post.step_status or dict(DEFAULT_STEP_STATUS),
            "created_at": post.created_at.isoformat() if post.created_at else None,
            "updated_at": post.updated_at.isoformat() if post.updated_at else None,
        }


_store: Optional[PostStore] = None


def get_store() -> PostStore:
    global _store
    if _store is None:
        _store = PostStore()
    return _store

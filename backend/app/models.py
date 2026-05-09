"""SQLAlchemy models for the production-oriented schema."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from app.db import Base
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class PostModel(Base):
    __tablename__ = "posts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    video_id: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    title: Mapped[str] = mapped_column(Text, default="", nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    video_context: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    step_status: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class PostTranscriptModel(Base):
    __tablename__ = "post_transcripts"

    post_id: Mapped[str] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True)
    storage_kind: Mapped[str] = mapped_column(String(32), default="database", nullable=False)
    transcript_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    object_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    char_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class PostContentModel(Base):
    __tablename__ = "post_contents"
    __table_args__ = (UniqueConstraint("post_id", "platform", name="uq_post_contents_post_platform"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    post_id: Mapped[str] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), index=True, nullable=False)
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    active_version_number: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class PostContentVersionModel(Base):
    __tablename__ = "post_content_versions"
    __table_args__ = (UniqueConstraint("content_id", "version_number", name="uq_content_versions_number"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    content_id: Mapped[str] = mapped_column(ForeignKey("post_contents.id", ondelete="CASCADE"), index=True, nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    body: Mapped[Any] = mapped_column(JSON, nullable=False)
    source: Mapped[str] = mapped_column(String(32), default="generated", nullable=False)
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class ContentRatingModel(Base):
    __tablename__ = "content_ratings"
    __table_args__ = (UniqueConstraint("content_version_id", "user_id", name="uq_content_rating_user"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    content_version_id: Mapped[str] = mapped_column(
        ForeignKey("post_content_versions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

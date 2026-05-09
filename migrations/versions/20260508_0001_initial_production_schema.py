"""initial production schema

Revision ID: 20260508_0001
Revises:
Create Date: 2026-05-08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260508_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "posts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("video_id", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("video_context", sa.JSON(), nullable=True),
        sa.Column("step_status", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_posts_user_id"), "posts", ["user_id"], unique=False)

    op.create_table(
        "post_transcripts",
        sa.Column("post_id", sa.String(length=36), nullable=False),
        sa.Column("storage_kind", sa.String(length=32), nullable=False),
        sa.Column("transcript_text", sa.Text(), nullable=False),
        sa.Column("object_key", sa.Text(), nullable=True),
        sa.Column("char_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("post_id"),
    )

    op.create_table(
        "post_contents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("post_id", sa.String(length=36), nullable=False),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("active_version_number", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("post_id", "platform", name="uq_post_contents_post_platform"),
    )
    op.create_index(op.f("ix_post_contents_post_id"), "post_contents", ["post_id"], unique=False)

    op.create_table(
        "post_content_versions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("content_id", sa.String(length=36), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("body", sa.JSON(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["content_id"], ["post_contents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("content_id", "version_number", name="uq_content_versions_number"),
    )
    op.create_index(
        op.f("ix_post_content_versions_content_id"),
        "post_content_versions",
        ["content_id"],
        unique=False,
    )

    op.create_table(
        "content_ratings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("content_version_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["content_version_id"], ["post_content_versions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("content_version_id", "user_id", name="uq_content_rating_user"),
    )
    op.create_index(
        op.f("ix_content_ratings_content_version_id"),
        "content_ratings",
        ["content_version_id"],
        unique=False,
    )
    op.create_index(op.f("ix_content_ratings_user_id"), "content_ratings", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_content_ratings_user_id"), table_name="content_ratings")
    op.drop_index(op.f("ix_content_ratings_content_version_id"), table_name="content_ratings")
    op.drop_table("content_ratings")
    op.drop_index(op.f("ix_post_content_versions_content_id"), table_name="post_content_versions")
    op.drop_table("post_content_versions")
    op.drop_index(op.f("ix_post_contents_post_id"), table_name="post_contents")
    op.drop_table("post_contents")
    op.drop_table("post_transcripts")
    op.drop_index(op.f("ix_posts_user_id"), table_name="posts")
    op.drop_table("posts")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")

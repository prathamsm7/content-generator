"""Database engine and session setup."""

from __future__ import annotations

from pathlib import Path

from app.settings import get_settings
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def normalize_database_url(database_url: str) -> str:
    """Make Neon/Postgres URLs work with SQLAlchemy's psycopg driver."""
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+psycopg://", 1)
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url


def build_database_url() -> str:
    configured_url = get_settings().database_url.strip() or "sqlite:///data/repurposely.db"
    database_url = normalize_database_url(configured_url)

    if database_url.startswith("sqlite:///"):
        sqlite_path = database_url.replace("sqlite:///", "", 1)
        sqlite_file = Path(sqlite_path)
        if not sqlite_file.is_absolute():
            sqlite_file = _repo_root() / sqlite_file
        sqlite_file.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{sqlite_file}"

    return database_url


class Base(DeclarativeBase):
    pass


DATABASE_URL = build_database_url()
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(engine, expire_on_commit=False)

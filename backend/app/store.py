"""In-memory job store with JSON persistence and per-job asyncio queues for SSE."""

from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path
from typing import Any, Optional

from app.settings import get_settings


def _repo_root() -> Path:
    # backend/app/store.py -> parents: app, backend, repo
    return Path(__file__).resolve().parent.parent.parent


def _jobs_dir() -> Path:
    s = get_settings()
    p = Path(s.jobs_dir)
    if not p.is_absolute():
        p = _repo_root() / p
    p.mkdir(parents=True, exist_ok=True)
    return p


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, dict[str, Any]] = {}
        self._queues: dict[str, asyncio.Queue[dict[str, Any]]] = {}
        self._lock = asyncio.Lock()

    def event_queue(self, job_id: str) -> asyncio.Queue[dict[str, Any]]:
        if job_id not in self._queues:
            self._queues[job_id] = asyncio.Queue()
        return self._queues[job_id]

    def create_job(self, url: str) -> str:
        job_id = str(uuid.uuid4())
        self._jobs[job_id] = {
            "job_id": job_id,
            "url": url,
            "video_id": "",
            "status": "pending",
            "error_message": None,
            "transcript": "",
            "title": "",
            "tags": [],
            "video_context": None,
            "linkedin_post": "",
            "twitter_post": None,
            "ratings": {},
            "step_status": {
                "transcription": "idle",
                "metadata": "idle",
                "linkedin": "idle",
                "twitter": "idle",
            },
        }
        self.event_queue(job_id)
        self._write_file(job_id)
        return job_id

    def get_job(self, job_id: str) -> Optional[dict[str, Any]]:
        if job_id in self._jobs:
            return self._jobs[job_id]
        data = self._read_file(job_id)
        if data:
            self._jobs[job_id] = data
            self.event_queue(job_id)
        return self._jobs.get(job_id)

    def require_job(self, job_id: str) -> dict[str, Any]:
        j = self.get_job(job_id)
        if not j:
            raise KeyError("job_not_found")
        return j

    def patch_job(self, job_id: str, **kwargs: Any) -> None:
        job = self.require_job(job_id)
        for k, v in kwargs.items():
            if v is not None or k in ("error_message", "twitter_post", "video_context"):
                job[k] = v

    def persist(self, job_id: str) -> None:
        self._write_file(job_id)

    def get_job_response(self, job_id: str) -> dict[str, Any]:
        j = self.require_job(job_id)
        return {
            "job_id": j["job_id"],
            "url": j["url"],
            "video_id": j["video_id"],
            "status": j["status"],
            "error_message": j.get("error_message"),
            "title": j.get("title"),
            "tags": j.get("tags"),
            "video_context": j.get("video_context"),
            "linkedin_post": j.get("linkedin_post"),
            "twitter_post": j.get("twitter_post"),
            "ratings": j.get("ratings") or {},
            "step_status": j.get("step_status")
            or {
                "transcription": "idle",
                "metadata": "idle",
                "linkedin": "idle",
                "twitter": "idle",
            },
        }

    def _path(self, job_id: str) -> Path:
        return _jobs_dir() / f"{job_id}.json"

    def _write_file(self, job_id: str) -> None:
        job = self._jobs.get(job_id)
        if not job:
            return
        path = self._path(job_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(job, f, ensure_ascii=False, indent=2, default=str)

    def _read_file(self, job_id: str) -> Optional[dict[str, Any]]:
        path = self._path(job_id)
        if not path.exists():
            return None
        with open(path, encoding="utf-8") as f:
            return json.load(f)


_store: Optional[JobStore] = None


def get_store() -> JobStore:
    global _store
    if _store is None:
        _store = JobStore()
    return _store

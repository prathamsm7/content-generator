# Repurposely

POC: turn a YouTube URL into LinkedIn and Twitter drafts with a FastAPI backend, LangGraph pipeline, PostgreSQL schema, and a Next.js UI.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Node 20+ and npm
- `OPENAI_API_KEY` in `.env` at the repo root (used by the backend)
- `DATABASE_URL` in `.env` for Neon/PostgreSQL.
- `JWT_SECRET_KEY` in `.env` for custom account auth.

Example `.env`:

```bash
OPENAI_API_KEY=...
DATABASE_URL=postgresql://USER:PASSWORD@HOST/neondb?sslmode=require
JWT_SECRET_KEY=replace-with-a-long-random-secret
```

If `DATABASE_URL` is not set, the backend uses a local SQLite file at `data/repurposely.db`.

## Run The App

From the repo root:

```bash
uv sync
npm install
cd frontend && npm install && cd ..
uv run alembic upgrade head
npm run dev
```

- API: `http://localhost:8000`
- App: `http://localhost:3000`
- Health: `GET /health`
- Auth: `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`
- Posts: `POST /api/posts`, `GET /api/posts`, `GET /api/posts/{post_id}`, `GET /api/posts/{post_id}/stream` (SSE), `PATCH /api/posts/{post_id}/content`, `POST /api/posts/{post_id}/rate`, `POST /api/posts/{post_id}/regenerate`

Post state is persisted in PostgreSQL through Alembic migrations. Local SQLite fallback files are gitignored.
- Set `NEXT_PUBLIC_API_BASE_URL` in `frontend/.env.local` if the API is not on `http://localhost:8000`.

## Flow

1. Login/register page: create a local JWT-backed account.
2. Home page: paste a YouTube URL and submit.
3. Post page: SSE shows progress for transcription, metadata/analysis, LinkedIn, and Twitter.
4. When complete: edit text, rate 1–5 stars, regenerate per platform, copy to clipboard.
5. History page: view user-scoped generated posts.

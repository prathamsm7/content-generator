# Repurposely

POC: turn a YouTube URL into LinkedIn and Twitter drafts with a FastAPI backend (LangGraph-style pipeline) and a Next.js UI.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Node 20+ and npm
- `OPENAI_API_KEY` in `.env` at the repo root (used by the backend)

## Run The App

From the repo root:

```bash
uv sync
npm install
cd frontend && npm install && cd ..
npm run dev
```

- API: `http://localhost:8000`
- App: `http://localhost:3000`
- Health: `GET /health`
- Jobs: `POST /api/jobs`, `GET /api/jobs/{id}`, `GET /api/jobs/{id}/stream` (SSE), `PATCH /api/jobs/{id}/content`, `POST /api/jobs/{id}/rate`, `POST /api/jobs/{id}/regenerate`

Job state is persisted under `data/jobs/` (gitignored).
- Set `NEXT_PUBLIC_API_BASE_URL` in `frontend/.env.local` if the API is not on `http://localhost:8000`.

## Flow

1. Home page: paste a YouTube URL and submit.
2. Job page: SSE shows progress for transcription, metadata/analysis, LinkedIn, and Twitter.
3. When complete: edit text, rate 1–5 stars, regenerate per platform, copy to clipboard.

## Notebooks

The original POC lives in `testv2.ipynb`. Pipeline code is mirrored under `backend/app/pipeline/`.

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.posts import router as posts_router
from app.settings import get_settings

app = FastAPI(title="Repurposely API", version="0.1.0")

_settings = get_settings()
_origins = [o.strip() for o in _settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins or ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(posts_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}

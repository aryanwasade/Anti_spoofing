"""
FastAPI application entry point.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.database import init_db
from backend.routers import session, report, ws

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Real-time antispoofing interview analysis system",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(session.router)
app.include_router(report.router)
app.include_router(ws.router)


# ── Startup ───────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    await init_db()
    print("[OK] Database initialized")
    print("[OK] Antispoofing backend ready")


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.APP_NAME}

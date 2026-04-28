from datetime import datetime, timezone

from fastapi import FastAPI

from app.api.v1.documents import router as documents_router
from app.db.init_db import init_db


app = FastAPI(
    title="HR Document Checker",
    description="Prototype of HR and business document checker with AI agents",
    version="0.1.0",
)


@app.on_event("startup")
def on_startup() -> None:
    """
    При старте приложения создаём таблицы БД, если их ещё нет.
    """

    init_db()


app.include_router(documents_router, prefix="/api/v1")


@app.get("/")
def root() -> dict[str, str]:
    return {
        "message": "HR Document Checker API is running"
    }


@app.get("/api/v1/health")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "project_name": "HR Document Checker",
        "app_env": "local",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
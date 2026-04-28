from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI

from app.api.v1.documents import router as documents_router
from app.db.init_db import init_db
from app.api.v1.rag import router as rag_router
from app.web.routes import router as web_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan-обработчик FastAPI.

    При старте приложения создаёт таблицы БД, если их ещё нет.
    Это современная замена устаревшего @app.on_event("startup").
    """

    init_db()
    yield


app = FastAPI(
    title="HR Document Checker",
    description="Prototype of HR and business document checker with AI agents",
    version="0.1.0",
    lifespan=lifespan,
)


app.include_router(documents_router, prefix="/api/v1")
app.include_router(rag_router, prefix="/api/v1")
app.include_router(web_router)


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
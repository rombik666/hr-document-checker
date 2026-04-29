from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI

from app.api.v1.documents import router as documents_router
from app.db.init_db import init_db
from app.api.v1.rag import router as rag_router
from app.web.routes import router as web_router
from app.api.v1.metrics import router as metrics_router
from app.core.logging import setup_logging
from app.middleware.request_logging import RequestLoggingMiddleware

from app.api.v1.admin import router as admin_router

from app.api.v1.llm import router as llm_router

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan-обработчик FastAPI.

    """

    setup_logging()
    init_db()
    yield


app = FastAPI(
    title="HR Document Checker",
    description="Prototype of HR and business document checker with AI agents",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(RequestLoggingMiddleware)

app.include_router(metrics_router, prefix="/api/v1")
app.include_router(documents_router, prefix="/api/v1")
app.include_router(rag_router, prefix="/api/v1")
app.include_router(web_router)
app.include_router(admin_router, prefix="/api/v1")
app.include_router(llm_router, prefix="/api/v1")


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
from datetime import datetime, timezone

from fastapi import FastAPI

from app.api.v1.documents import router as documents_router


app = FastAPI(
    title="HR Document Checker",
    description="Prototype of HR and business document checker with AI agents",
    version="0.1.0",
)


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
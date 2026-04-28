from fastapi import APIRouter

from app.core.metrics import metrics
from app.schemas.metrics import MetricsSnapshot


router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("", response_model=MetricsSnapshot)
def get_metrics() -> MetricsSnapshot:
    """
    Возвращает базовые метрики приложения.

    """

    return MetricsSnapshot.model_validate(metrics.snapshot())
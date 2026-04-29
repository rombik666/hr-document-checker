from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from app.core.metrics import metrics
from app.schemas.metrics import MetricsSnapshot


router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("", response_model=MetricsSnapshot)
def get_metrics() -> MetricsSnapshot:

    return MetricsSnapshot.model_validate(metrics.snapshot())


@router.get("/prometheus", response_class=PlainTextResponse)
def get_prometheus_metrics() -> PlainTextResponse:

    snapshot = metrics.snapshot()

    lines = [
        "# HELP requests_total Total number of HTTP requests.",
        "# TYPE requests_total counter",
        f"requests_total {snapshot['requests_total']}",
        "",
        "# HELP documents_processed_total Total number of processed documents.",
        "# TYPE documents_processed_total counter",
        f"documents_processed_total {snapshot['documents_processed_total']}",
        "",
        "# HELP reports_generated_total Total number of generated reports.",
        "# TYPE reports_generated_total counter",
        f"reports_generated_total {snapshot['reports_generated_total']}",
        "",
        "# HELP errors_total Total number of application errors.",
        "# TYPE errors_total counter",
        f"errors_total {snapshot['errors_total']}",
        "",
        "# HELP issues_found_total Total number of issues found in documents.",
        "# TYPE issues_found_total counter",
        f"issues_found_total {snapshot['issues_found_total']}",
        "",
        "# HELP average_request_time_ms Average request processing time in milliseconds.",
        "# TYPE average_request_time_ms gauge",
        f"average_request_time_ms {snapshot['average_request_time_ms']}",
        "",
        "# HELP average_document_processing_time_ms Average document processing time in milliseconds.",
        "# TYPE average_document_processing_time_ms gauge",
        (
            "average_document_processing_time_ms "
            f"{snapshot['average_document_processing_time_ms']}"
        ),
        "",
    ]

    content = "\n".join(lines) + "\n"

    return PlainTextResponse(
        content=content,
        media_type="text/plain; version=0.0.4",
    )
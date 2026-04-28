from pydantic import BaseModel


class MetricsSnapshot(BaseModel):
    """
    Снимок текущих метрик приложения.
    """

    requests_total: int
    documents_processed_total: int
    reports_generated_total: int
    errors_total: int
    issues_found_total: int
    average_request_time_ms: float
    average_document_processing_time_ms: float
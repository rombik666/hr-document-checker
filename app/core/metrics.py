from threading import Lock


class AppMetrics:
    """
    Простое in-memory хранилище метрик.

    Для MVP этого достаточно.
    Позже эти же метрики можно отдавать в Prometheus/Grafana.
    """

    def __init__(self) -> None:
        self._lock = Lock()

        self.requests_total = 0
        self.documents_processed_total = 0
        self.reports_generated_total = 0
        self.errors_total = 0

        self.total_request_time_ms = 0.0
        self.total_document_processing_time_ms = 0.0

        self.issues_found_total = 0

    def record_request(
        self,
        duration_ms: float,
        is_error: bool = False,
    ) -> None:
        with self._lock:
            self.requests_total += 1
            self.total_request_time_ms += duration_ms

            if is_error:
                self.errors_total += 1

    def record_document_processed(
        self,
        duration_ms: float,
        issues_count: int = 0,
    ) -> None:
        with self._lock:
            self.documents_processed_total += 1
            self.total_document_processing_time_ms += duration_ms
            self.issues_found_total += issues_count

    def record_report_generated(self) -> None:
        with self._lock:
            self.reports_generated_total += 1

    def record_error(self) -> None:
        with self._lock:
            self.errors_total += 1

    def snapshot(self) -> dict:
        with self._lock:
            average_request_time_ms = (
                self.total_request_time_ms / self.requests_total
                if self.requests_total
                else 0.0
            )

            average_document_processing_time_ms = (
                self.total_document_processing_time_ms / self.documents_processed_total
                if self.documents_processed_total
                else 0.0
            )

            return {
                "requests_total": self.requests_total,
                "documents_processed_total": self.documents_processed_total,
                "reports_generated_total": self.reports_generated_total,
                "errors_total": self.errors_total,
                "issues_found_total": self.issues_found_total,
                "average_request_time_ms": round(average_request_time_ms, 3),
                "average_document_processing_time_ms": round(
                    average_document_processing_time_ms,
                    3,
                ),
            }


metrics = AppMetrics()
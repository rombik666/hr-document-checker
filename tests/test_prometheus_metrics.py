from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_prometheus_metrics_endpoint_returns_text_metrics() -> None:
    response = client.get("/api/v1/metrics/prometheus")

    assert response.status_code == 200

    content = response.text

    assert "requests_total" in content
    assert "documents_processed_total" in content
    assert "reports_generated_total" in content
    assert "errors_total" in content
    assert "issues_found_total" in content
    assert "average_request_time_ms" in content
    assert "average_document_processing_time_ms" in content
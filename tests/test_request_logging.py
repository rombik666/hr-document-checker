from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_response_contains_request_id_header() -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert "x-request-id" in response.headers
    assert response.headers["x-request-id"]
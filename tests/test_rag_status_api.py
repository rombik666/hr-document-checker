from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_rag_status_endpoint_returns_status() -> None:
    response = client.get("/api/v1/rag/status")

    assert response.status_code == 200

    data = response.json()

    assert "knowledge_base_dir" in data
    assert "sources_count" in data
    assert "chunks_count" in data
    assert data["retriever_type"] in {"vector", "simple"}
from fastapi.testclient import TestClient
from tests.auth_helpers import auth_headers
from app.main import app


client = TestClient(app)


def test_rag_status_endpoint_returns_status() -> None:
    response = client.get(
        "/api/v1/rag/status",
        headers=auth_headers(client, "hr"),
    )

    assert response.status_code == 200

    data = response.json()

    assert "knowledge_base_dir" in data
    assert "sources_count" in data
    assert "chunks_count" in data
    assert data["retriever_type"] in {"faiss", "vector", "simple"}
    assert "index_exists" in data
    assert "embedding_backend" in data
    assert "index_dir" in data
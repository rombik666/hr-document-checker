from fastapi.testclient import TestClient

from app.main import app
from tests.auth_helpers import auth_headers


client = TestClient(app)


def test_rag_status_endpoint_returns_per_user_faiss_status() -> None:
    response = client.get(
        "/api/v1/rag/status",
        headers=auth_headers(client, "hr"),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["mode"] == "per_user_faiss"
    assert data["source_backend"] == "database+filesystem"
    assert data["user_scope"] == "current_user"

    assert "knowledge_base_dir" in data
    assert "sources_count" in data
    assert "active_sources_count" in data
    assert "inactive_sources_count" in data
    assert "chunks_count" in data

    assert data["retriever_type"] == "faiss"
    assert "index_exists" in data
    assert "reindex_required" in data
    assert "embedding_backend" in data
    assert "embedding_model_name" in data
    assert "embedding_dimension" in data
    assert "index_dir" in data

    assert data["index_status"] in {
        "missing",
        "stale",
        "building",
        "ready",
        "failed",
    }
    assert data["index_owner_user_id"]
    assert "index_path" in data
    assert "chunks_path" in data
    assert "sources_hash" in data
    assert "last_reindexed_at" in data
    assert "index_error" in data


def test_candidate_cannot_get_rag_status() -> None:
    response = client.get(
        "/api/v1/rag/status",
        headers=auth_headers(client, "candidate"),
    )

    assert response.status_code == 403
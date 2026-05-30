from fastapi.testclient import TestClient

from app.main import app
from tests.auth_helpers import auth_headers


client = TestClient(app)


def test_rag_search_endpoint_requires_ready_personal_index() -> None:
    response = client.post(
        "/api/v1/rag/search",
        headers=auth_headers(client, "hr"),
        json={
            "query": "python backend fastapi docker",
            "top_k": 3,
        },
    )

    assert response.status_code == 409

    detail = response.json()["detail"]

    assert detail["error"] == "rag_reindex_required"
    assert detail["index_status"] in {
        "missing",
        "stale",
        "building",
        "failed",
    }
    assert detail["reindex_required"] is True
    assert detail["reindex_endpoint"] == "/api/v1/rag/reindex"


def test_candidate_cannot_search_rag_context() -> None:
    response = client.post(
        "/api/v1/rag/search",
        headers=auth_headers(client, "candidate"),
        json={
            "query": "python backend fastapi docker",
            "top_k": 3,
        },
    )

    assert response.status_code == 403
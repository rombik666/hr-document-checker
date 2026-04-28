from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_rag_search_endpoint_returns_context() -> None:
    response = client.post(
        "/api/v1/rag/search",
        json={
            "query": "python backend fastapi docker",
            "top_k": 3,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["query"] == "python backend fastapi docker"
    assert "results" in data
    assert isinstance(data["results"], list)
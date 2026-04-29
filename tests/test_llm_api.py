from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_llm_status_endpoint_returns_status() -> None:
    response = client.get("/api/v1/llm/status")

    assert response.status_code == 200

    data = response.json()

    assert "enabled" in data
    assert "provider" in data
    assert "model" in data
    assert "available" in data


def test_llm_generate_endpoint_returns_text() -> None:
    response = client.post(
        "/api/v1/llm/generate",
        json={
            "system_prompt": "You are an HR document checking agent.",
            "prompt": "Analyze this CV.",
            "temperature": 0.1,
            "max_tokens": 100,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert "provider" in data
    assert "model" in data
    assert "text" in data
    assert data["text"]
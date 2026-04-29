from fastapi.testclient import TestClient

from app.main import app
from tests.auth_helpers import admin_auth_headers, auth_headers


client = TestClient(app)


def test_candidate_cannot_access_rag_status() -> None:
    response = client.get(
        "/api/v1/rag/status",
        headers=auth_headers(client, "candidate"),
    )

    assert response.status_code == 403


def test_hr_can_access_rag_status() -> None:
    response = client.get(
        "/api/v1/rag/status",
        headers=auth_headers(client, "hr"),
    )

    assert response.status_code == 200


def test_candidate_cannot_access_admin_status() -> None:
    response = client.get(
        "/api/v1/admin/status",
        headers=auth_headers(client, "candidate"),
    )

    assert response.status_code == 403


def test_hr_cannot_access_admin_status() -> None:
    response = client.get(
        "/api/v1/admin/status",
        headers=auth_headers(client, "hr"),
    )

    assert response.status_code == 403


def test_admin_can_access_admin_status() -> None:
    response = client.get(
        "/api/v1/admin/status",
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200
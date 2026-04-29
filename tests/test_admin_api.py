from fastapi.testclient import TestClient

from tests.auth_helpers import auth_headers
from tests.auth_helpers import admin_auth_headers
from app.main import app


client = TestClient(app)


def test_admin_status_endpoint_returns_ok() -> None:
    response = client.get(
        "/api/v1/admin/status", 
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"
    assert data["service"] == "admin"


def test_admin_roles_endpoint_returns_roles() -> None:
    response = client.get(
        "/api/v1/admin/roles",
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200

    data = response.json()
    roles = {
        item["role"]
        for item in data["roles"]
    }

    assert "candidate" in roles
    assert "hr" in roles
    assert "admin" in roles


def test_admin_database_status_endpoint_returns_diagnostics() -> None:
    response = client.get(
        "/api/v1/admin/db/status",
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["database_available"] is True
    assert "documents_count" in data
    assert "reports_count" in data
    assert data["raw_text_column_exists"] is False


def test_admin_privacy_check_endpoint_returns_result() -> None:
    response = client.get(
        "/api/v1/admin/storage/privacy-check",
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200

    data = response.json()

    assert "passed" in data
    assert "checked_reports" in data
    assert "unmasked_email_count" in data
    assert "unmasked_phone_count" in data
    assert data["raw_text_column_exists"] is False
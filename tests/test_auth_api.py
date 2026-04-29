from fastapi.testclient import TestClient
from tests.auth_helpers import auth_headers
from app.main import app


client = TestClient(app)


def test_register_candidate_and_get_me() -> None:
    response = client.post(
        "/api/v1/auth/register",
        headers=auth_headers(client, "candidate"),
        json={
            "email": "candidate-auth-test@example.com",
            "full_name": "Candidate Test",
            "password": "123456",
            "role": "candidate",
        },
    )

    assert response.status_code in {200, 400}

    if response.status_code == 400:
        login_response = client.post(
            "/api/v1/auth/login",
            headers=auth_headers(client, "candidate"),
            json={
                "email": "candidate-auth-test@example.com",
                "password": "123456",
            },
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
    else:
        token = response.json()["access_token"]

    me_response = client.get(
        "/api/v1/auth/me",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert me_response.status_code == 200
    assert me_response.json()["email"] == "candidate-auth-test@example.com"
    assert me_response.json()["role"] == "candidate"


def test_public_registration_cannot_create_admin() -> None:
    response = client.post(
        "/api/v1/auth/register",
        headers=auth_headers(client, "candidate"),
        json={
            "email": "admin-registration-test@example.com",
            "full_name": "Admin Registration Test",
            "password": "123456",
            "role": "admin",
        },
    )

    assert response.status_code == 400


def test_login_with_wrong_password_returns_401() -> None:
    response = client.post(
        "/api/v1/auth/login",
        headers=auth_headers(client, "candidate"),
        json={
            "email": "candidate-auth-test@example.com",
            "password": "wrong-password",
        },
    )

    assert response.status_code == 401
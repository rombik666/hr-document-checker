from urllib.parse import parse_qs, urlparse
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.services.password_reset_email_service import PasswordResetEmailService


client = TestClient(app)


def _register_user(
    email: str,
    password: str = "123456",
) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": "Password Reset Web User",
            "password": password,
            "role": "candidate",
        },
    )

    assert response.status_code == 200


def _token_from_reset_url(reset_url: str) -> str:
    query = parse_qs(urlparse(reset_url).query)
    token_values = query.get("token")

    assert token_values

    return token_values[0]


def test_login_page_links_to_password_reset() -> None:
    response = client.get("/web/login")

    assert response.status_code == 200
    assert 'href="/web/password-reset/request"' in response.text


def test_web_password_reset_request_page_returns_form() -> None:
    response = client.get("/web/password-reset/request")

    assert response.status_code == 200
    assert 'action="/web/password-reset/request"' in response.text
    assert 'name="email"' in response.text


def test_web_password_reset_sends_link_and_changes_password(monkeypatch) -> None:
    sent_links: list[tuple[str, str]] = []

    def fake_send_reset_link(
        self,
        recipient_email: str,
        reset_url: str,
    ) -> None:
        sent_links.append((recipient_email, reset_url))

    monkeypatch.setattr(
        PasswordResetEmailService,
        "send_reset_link",
        fake_send_reset_link,
    )

    email = f"web-reset-{uuid4().hex}@example.com"
    _register_user(email, password="old-password")

    request_response = client.post(
        "/web/password-reset/request",
        data={"email": email},
    )

    assert request_response.status_code == 200
    assert "Если активный аккаунт с таким email существует" in request_response.text
    assert len(sent_links) == 1
    assert sent_links[0][0] == email

    token = _token_from_reset_url(sent_links[0][1])

    form_response = client.get(f"/web/password-reset/confirm?token={token}")

    assert form_response.status_code == 200
    assert 'action="/web/password-reset/confirm"' in form_response.text
    assert 'name="new_password"' in form_response.text
    assert 'name="new_password_confirm"' in form_response.text

    mismatch_response = client.post(
        "/web/password-reset/confirm",
        data={
            "token": token,
            "new_password": "new-password",
            "new_password_confirm": "other-password",
        },
    )

    assert mismatch_response.status_code == 400
    assert "Пароли не совпадают" in mismatch_response.text

    confirm_response = client.post(
        "/web/password-reset/confirm",
        data={
            "token": token,
            "new_password": "new-password",
            "new_password_confirm": "new-password",
        },
        follow_redirects=False,
    )

    assert confirm_response.status_code == 303
    assert confirm_response.headers["location"] == "/web/login?password_reset=success"

    login_page_response = client.get(confirm_response.headers["location"])

    assert login_page_response.status_code == 200
    assert "Пароль обновлён" in login_page_response.text

    old_login_response = client.post(
        "/web/login",
        data={
            "email": email,
            "password": "old-password",
        },
    )
    new_login_response = client.post(
        "/web/login",
        data={
            "email": email,
            "password": "new-password",
        },
        follow_redirects=False,
    )
    reused_token_response = client.get(f"/web/password-reset/confirm?token={token}")

    assert old_login_response.status_code == 401
    assert new_login_response.status_code == 303
    assert new_login_response.headers["location"] == "/web/dashboard"
    assert reused_token_response.status_code == 400
    assert "недействительна или истекла" in reused_token_response.text


def test_web_password_reset_request_is_generic_for_missing_email(monkeypatch) -> None:
    sent_links: list[tuple[str, str]] = []

    def fake_send_reset_link(
        self,
        recipient_email: str,
        reset_url: str,
    ) -> None:
        sent_links.append((recipient_email, reset_url))

    monkeypatch.setattr(
        PasswordResetEmailService,
        "send_reset_link",
        fake_send_reset_link,
    )

    response = client.post(
        "/web/password-reset/request",
        data={"email": f"missing-{uuid4().hex}@example.com"},
    )

    assert response.status_code == 200
    assert "Если активный аккаунт с таким email существует" in response.text
    assert sent_links == []

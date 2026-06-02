from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.auth.security import hash_security_token
from app.db.models import PasswordResetTokenORM
from app.db.session import SessionLocal
from app.main import app
from app.services.password_reset_email_service import PasswordResetEmailService
from app.services.password_reset_service import PasswordResetService
from app.services.user_service import UserService


client = TestClient(app)


def _register_user(
    email: str,
    password: str = "123456",
) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": "Password Reset User",
            "password": password,
            "role": "candidate",
        },
    )

    assert response.status_code == 200


def _create_reset_token(email: str) -> str:
    db = SessionLocal()

    try:
        token = PasswordResetService(db).create_reset_token(email)
        assert token is not None

        return token
    finally:
        db.close()


def test_password_reset_request_has_generic_response(monkeypatch) -> None:
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

    email = f"reset-generic-{uuid4().hex}@example.com"
    _register_user(email)

    existing_response = client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": email},
    )
    missing_response = client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": f"missing-{uuid4().hex}@example.com"},
    )

    assert existing_response.status_code == 200
    assert missing_response.status_code == 200
    assert existing_response.json() == missing_response.json()
    assert "reset_token" not in existing_response.json()
    assert len(sent_links) == 1
    assert sent_links[0][0] == email
    assert "/web/password-reset/confirm?" in sent_links[0][1]


def test_password_can_be_reset_with_one_time_token() -> None:
    email = f"reset-success-{uuid4().hex}@example.com"
    _register_user(email, password="old-password")
    token = _create_reset_token(email)

    response = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={
            "token": token,
            "new_password": "new-password",
        },
    )

    assert response.status_code == 200

    old_login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "old-password",
        },
    )
    new_login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "new-password",
        },
    )
    reuse_response = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={
            "token": token,
            "new_password": "another-password",
        },
    )

    assert old_login_response.status_code == 401
    assert new_login_response.status_code == 200
    assert reuse_response.status_code == 400


def test_password_reset_rejects_invalid_and_expired_tokens() -> None:
    email = f"reset-expired-{uuid4().hex}@example.com"
    _register_user(email)
    token = _create_reset_token(email)

    invalid_response = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={
            "token": "invalid-token-with-enough-characters-1234567890",
            "new_password": "new-password",
        },
    )

    db = SessionLocal()

    try:
        user = UserService(db).get_by_email(email)
        assert user is not None
        statement = select(PasswordResetTokenORM).where(
            PasswordResetTokenORM.user_id == user.id,
        )
        reset_token = db.execute(statement).scalar_one()
        reset_token.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()
    finally:
        db.close()

    expired_response = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={
            "token": token,
            "new_password": "new-password",
        },
    )

    assert invalid_response.status_code == 400
    assert expired_response.status_code == 400


def test_password_reset_token_is_stored_as_hash() -> None:
    email = f"reset-hash-{uuid4().hex}@example.com"
    _register_user(email)
    token = _create_reset_token(email)

    db = SessionLocal()

    try:
        token_hash = hash_security_token(token)
        statement = select(PasswordResetTokenORM).where(
            PasswordResetTokenORM.token_hash == token_hash,
        )
        reset_token = db.execute(statement).scalar_one()

        assert reset_token.token_hash == token_hash
        assert reset_token.token_hash != token
    finally:
        db.close()

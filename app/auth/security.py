import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.config import settings


PASSWORD_ITERATIONS = 210_000


def hash_password(password: str) -> str:

    salt = secrets.token_hex(16)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PASSWORD_ITERATIONS,
    ).hex()

    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${salt}${password_hash}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations_raw, salt, expected_hash = stored_hash.split("$")
    except ValueError:
        return False

    if algorithm != "pbkdf2_sha256":
        return False

    try:
        iterations = int(iterations_raw)
    except ValueError:
        return False

    actual_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    ).hex()

    return hmac.compare_digest(actual_hash, expected_hash)


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _sign(data: str) -> str:
    signature = hmac.new(
        settings.auth_secret_key.encode("utf-8"),
        data.encode("utf-8"),
        hashlib.sha256,
    ).digest()

    return _b64encode(signature)


def create_access_token(
    user_id: str,
    email: str,
    role: str,
) -> str:

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=settings.auth_token_ttl_minutes)

    header = {
        "typ": "JWT",
        "alg": "HS256",
    }

    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }

    header_part = _b64encode(
        json.dumps(header, separators=(",", ":")).encode("utf-8")
    )
    payload_part = _b64encode(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    )

    unsigned_token = f"{header_part}.{payload_part}"
    signature = _sign(unsigned_token)

    return f"{unsigned_token}.{signature}"


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        header_part, payload_part, signature = token.split(".")
    except ValueError as error:
        raise ValueError("Invalid token format.") from error

    unsigned_token = f"{header_part}.{payload_part}"
    expected_signature = _sign(unsigned_token)

    if not hmac.compare_digest(signature, expected_signature):
        raise ValueError("Invalid token signature.")

    payload = json.loads(_b64decode(payload_part).decode("utf-8"))

    expires_at = int(payload.get("exp", 0))
    now = int(datetime.now(timezone.utc).timestamp())

    if expires_at < now:
        raise ValueError("Token expired.")

    return payload
from urllib.parse import urlencode

from fastapi import Request

from app.core.config import settings


def build_password_reset_url(
    request: Request,
    token: str,
) -> str:
    base_url = settings.public_base_url or str(request.base_url)
    base_url = base_url.rstrip("/")
    query = urlencode({"token": token})

    return f"{base_url}/web/password-reset/confirm?{query}"

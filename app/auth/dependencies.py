from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.auth.security import decode_access_token
from app.db.models import UserORM
from app.db.session import get_db
from app.services.user_service import UserService


AUTH_COOKIE_NAME = "access_token"

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False,
)


def _extract_token(
    request: Request,
    bearer_token: str | None,
) -> str | None:
    if bearer_token:
        return bearer_token

    cookie_token = request.cookies.get(AUTH_COOKIE_NAME)

    if cookie_token:
        return cookie_token

    return None


def get_current_user(
    request: Request,
    bearer_token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> UserORM:
    token = _extract_token(
        request=request,
        bearer_token=bearer_token,
    )

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    try:
        payload = decode_access_token(token)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(error),
        ) from error

    user_id = str(payload.get("sub", ""))
    user = UserService(db).get_by_id(user_id)

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is not active or does not exist.",
        )

    return user


def require_roles(*allowed_roles: str):
    def dependency(
        user: UserORM = Depends(get_current_user),
    ) -> UserORM:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions.",
            )

        return user

    return dependency


require_candidate_or_hr_or_admin = require_roles(
    "candidate",
    "hr",
    "admin",
)

require_hr_or_admin = require_roles(
    "hr",
    "admin",
)

require_admin = require_roles(
    "admin",
)
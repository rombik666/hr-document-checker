from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import AUTH_COOKIE_NAME, get_current_user
from app.auth.security import create_access_token
from app.core.logging import get_logger
from app.db.models import UserORM
from app.db.session import get_db
from app.schemas.auth import (
    AuthTokenResponse,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    PasswordResetResponse,
    UserCreateRequest,
    UserLoginRequest,
    UserResponse,
)
from app.services.password_reset_email_service import PasswordResetEmailService
from app.services.password_reset_link_service import build_password_reset_url
from app.services.password_reset_service import PasswordResetService
from app.services.user_service import UserService


router = APIRouter(prefix="/auth", tags=["auth"])
logger = get_logger(__name__)


def _to_user_response(user: UserORM) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
    )


def _create_auth_response(
    user: UserORM,
    response: Response,
) -> AuthTokenResponse:
    access_token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
    )

    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=access_token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 12,
    )

    return AuthTokenResponse(
        access_token=access_token,
        user=_to_user_response(user),
    )


@router.post("/register", response_model=AuthTokenResponse)
def register_user(
    request: UserCreateRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> AuthTokenResponse:
    try:
        user = UserService(db).create_user(request)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    return _create_auth_response(user, response)


@router.post("/login", response_model=AuthTokenResponse)
def login_user(
    request: UserLoginRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> AuthTokenResponse:
    user = UserService(db).authenticate(
        email=request.email,
        password=request.password,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    return _create_auth_response(user, response)


@router.post("/logout")
def logout_user(response: Response) -> dict[str, str]:
    response.delete_cookie(AUTH_COOKIE_NAME)

    return {
        "status": "ok",
        "message": "Logged out.",
    }


@router.post("/password-reset/request", response_model=PasswordResetResponse)
def request_password_reset(
    http_request: Request,
    request: PasswordResetRequest,
    db: Session = Depends(get_db),
) -> PasswordResetResponse:
    token = PasswordResetService(db).create_reset_token(request.email)

    if token is not None:
        reset_url = build_password_reset_url(http_request, token)

        try:
            PasswordResetEmailService().send_reset_link(
                recipient_email=str(request.email),
                reset_url=reset_url,
            )
        except RuntimeError as error:
            logger.warning(
                "password_reset_email_not_configured email=%s error=%s reset_url=%s",
                request.email,
                error,
                reset_url,
            )
        except Exception:
            logger.exception("password_reset_email_send_failed email=%s", request.email)

    return PasswordResetResponse(
        status="ok",
        message="If an active account with this email exists, password reset instructions are ready.",
    )


@router.post("/password-reset/confirm", response_model=PasswordResetResponse)
def confirm_password_reset(
    request: PasswordResetConfirmRequest,
    db: Session = Depends(get_db),
) -> PasswordResetResponse:
    was_reset = PasswordResetService(db).reset_password(
        token=request.token,
        new_password=request.new_password,
    )

    if not was_reset:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token.",
        )

    return PasswordResetResponse(
        status="ok",
        message="Password has been reset.",
    )


@router.get("/me", response_model=UserResponse)
def get_me(
    user: UserORM = Depends(get_current_user),
) -> UserResponse:
    return _to_user_response(user)

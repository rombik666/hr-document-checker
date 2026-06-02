from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import generate_secure_token, hash_password, hash_security_token
from app.core.config import settings
from app.db.models import PasswordResetTokenORM
from app.services.user_service import UserService


class PasswordResetService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_reset_token(self, email: str) -> str | None:
        user = UserService(self.db).get_by_email(email)

        if user is None or not user.is_active:
            return None

        now = self._now()
        self._invalidate_user_tokens(user.id, now)

        raw_token = generate_secure_token()
        reset_token = PasswordResetTokenORM(
            id=str(uuid4()),
            user_id=user.id,
            token_hash=hash_security_token(raw_token),
            expires_at=now + timedelta(minutes=settings.password_reset_token_ttl_minutes),
        )

        self.db.add(reset_token)
        self.db.commit()

        return raw_token

    def reset_password(
        self,
        token: str,
        new_password: str,
    ) -> bool:
        reset_token = self._get_valid_reset_token(token)

        if reset_token is None:
            return False

        now = self._now()

        user = reset_token.user

        if user is None or not user.is_active:
            return False

        user.password_hash = hash_password(new_password)
        reset_token.used_at = now
        self.db.commit()

        return True

    def is_token_valid(self, token: str) -> bool:
        return self._get_valid_reset_token(token) is not None

    def _get_valid_reset_token(self, token: str) -> PasswordResetTokenORM | None:
        token_hash = hash_security_token(token)
        statement = select(PasswordResetTokenORM).where(
            PasswordResetTokenORM.token_hash == token_hash,
        )
        reset_token = self.db.execute(statement).scalar_one_or_none()

        if reset_token is None:
            return None

        if reset_token.used_at is not None:
            return None

        if self._as_aware(reset_token.expires_at) < self._now():
            return None

        return reset_token

    def _invalidate_user_tokens(
        self,
        user_id: str,
        used_at: datetime,
    ) -> None:
        statement = select(PasswordResetTokenORM).where(
            PasswordResetTokenORM.user_id == user_id,
            PasswordResetTokenORM.used_at.is_(None),
        )

        for reset_token in self.db.execute(statement).scalars():
            reset_token.used_at = used_at

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _as_aware(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)

        return value

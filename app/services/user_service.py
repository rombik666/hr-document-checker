from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import hash_password, verify_password
from app.db.models import UserORM, UserRole
from app.schemas.auth import AuthUserRole, UserCreateRequest


class UserService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_email(self, email: str) -> UserORM | None:
        statement = select(UserORM).where(UserORM.email == email.lower())
        return self.db.execute(statement).scalar_one_or_none()

    def get_by_id(self, user_id: str) -> UserORM | None:
        return self.db.get(UserORM, user_id)

    def create_user(self, request: UserCreateRequest) -> UserORM:
        existing_user = self.get_by_email(request.email)

        if existing_user is not None:
            raise ValueError("User with this email already exists.")

        if request.role == AuthUserRole.ADMIN:
            raise ValueError("Admin user cannot be created through public registration.")

        user = UserORM(
            id=str(uuid4()),
            email=request.email.lower(),
            full_name=request.full_name.strip(),
            role=request.role.value,
            password_hash=hash_password(request.password),
            is_active=True,
        )

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        return user

    def authenticate(
        self,
        email: str,
        password: str,
    ) -> UserORM | None:
        user = self.get_by_email(email)

        if user is None:
            return None

        if not user.is_active:
            return None

        if not verify_password(password, user.password_hash):
            return None

        return user

    def ensure_admin_user(
        self,
        email: str,
        password: str,
        full_name: str,
    ) -> UserORM:
        existing_admin = self.get_by_email(email)

        if existing_admin is not None:
            return existing_admin

        admin = UserORM(
            id=str(uuid4()),
            email=email.lower(),
            full_name=full_name.strip(),
            role=UserRole.ADMIN.value,
            password_hash=hash_password(password),
            is_active=True,
        )

        self.db.add(admin)
        self.db.commit()
        self.db.refresh(admin)

        return admin
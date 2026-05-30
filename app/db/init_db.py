from app.core.config import settings
from app.db.session import SessionLocal
from app.services.user_service import UserService


def init_db() -> None:
    """
    Инициализирует системные данные.

    Физическая схема БД создаётся и обновляется миграциями Alembic.
    На старте Docker-контейнера выполняется alembic upgrade head.
    """

    db = SessionLocal()

    try:
        UserService(db).ensure_admin_user(
            email=settings.admin_email,
            password=settings.admin_password,
            full_name=settings.admin_full_name,
        )
    finally:
        db.close()
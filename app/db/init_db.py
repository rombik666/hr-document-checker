from app.core.config import settings
from app.db.models import Base
from app.db.session import SessionLocal, engine
from app.services.user_service import UserService


def init_db() -> None:
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        UserService(db).ensure_admin_user(
            email=settings.admin_email,
            password=settings.admin_password,
            full_name=settings.admin_full_name,
        )
    finally:
        db.close()
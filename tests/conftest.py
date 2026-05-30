import pytest

from app.core.config import settings
from app.db.init_db import init_db
from app.db.models import Base
from app.db.session import engine


@pytest.fixture(scope="session", autouse=True)
def prepare_test_database() -> None:
    """
    Подготавливает тестовую SQLite-БД.

    В production и Docker физическая схема создаётся Alembic-миграциями.
    В unit/integration тестах на SQLite схема создаётся через SQLAlchemy metadata
    для быстрого и изолированного прогона тестов.
    """

    if settings.database_url.startswith("sqlite"):
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)

    init_db()
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Base, RagIndexORM, RagIndexStatus, UserORM
from app.services.rag_source_service import RagSourceService


def make_test_db() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={
            "check_same_thread": False,
        },
    )

    Base.metadata.create_all(bind=engine)

    session_local = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )

    return session_local()


def create_user(db: Session, user_id: str = "hr-user-1") -> UserORM:
    user = UserORM(
        id=user_id,
        email=f"{user_id}@example.com",
        full_name=f"User {user_id}",
        role="hr",
        password_hash="test-password-hash",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def make_text_file(tmp_path: Path, filename: str, content: str) -> Path:
    file_path = tmp_path / filename
    file_path.write_text(content, encoding="utf-8")

    return file_path


def get_rag_index(db: Session, owner_user_id: str) -> RagIndexORM | None:
    return (
        db.query(RagIndexORM)
        .filter(RagIndexORM.owner_user_id == owner_user_id)
        .one_or_none()
    )


def test_upload_source_marks_user_rag_index_stale(tmp_path: Path) -> None:
    db = make_test_db()

    try:
        create_user(db, "hr-user-1")

        file_path = make_text_file(
            tmp_path=tmp_path,
            filename="vacancy.txt",
            content="Требования вакансии: Python, FastAPI, PostgreSQL.",
        )

        service = RagSourceService(db)

        service.create_source_from_file(
            file_path=file_path,
            original_filename="vacancy.txt",
            owner_user_id="hr-user-1",
            title="Backend vacancy",
            source_type="vacancy",
        )

        rag_index = get_rag_index(db, "hr-user-1")

        assert rag_index is not None
        assert rag_index.status == RagIndexStatus.STALE.value
        assert rag_index.reindex_required is True
        assert rag_index.sources_count == 1
        assert rag_index.sources_hash is not None

    finally:
        db.close()


def test_deactivate_source_marks_user_rag_index_stale(tmp_path: Path) -> None:
    db = make_test_db()

    try:
        create_user(db, "hr-user-1")

        file_path = make_text_file(
            tmp_path=tmp_path,
            filename="policy.txt",
            content="Корпоративный чек-лист проверки резюме.",
        )

        service = RagSourceService(db)

        source = service.create_source_from_file(
            file_path=file_path,
            original_filename="policy.txt",
            owner_user_id="hr-user-1",
            title="CV policy",
            source_type="policy",
        )

        deactivated = service.deactivate_source_for_user(
            source_id=source.id,
            user_id="hr-user-1",
            user_role="hr",
        )

        assert deactivated is True

        rag_index = get_rag_index(db, "hr-user-1")

        assert rag_index is not None
        assert rag_index.status == RagIndexStatus.STALE.value
        assert rag_index.reindex_required is True
        assert rag_index.sources_count == 0
        assert rag_index.sources_hash is not None

    finally:
        db.close()


def test_activate_source_marks_user_rag_index_stale(tmp_path: Path) -> None:
    db = make_test_db()

    try:
        create_user(db, "hr-user-1")

        file_path = make_text_file(
            tmp_path=tmp_path,
            filename="requirements.txt",
            content="Требования: Python, Docker, PostgreSQL.",
        )

        service = RagSourceService(db)

        source = service.create_source_from_file(
            file_path=file_path,
            original_filename="requirements.txt",
            owner_user_id="hr-user-1",
            title="Backend requirements",
            source_type="requirements",
        )

        deactivated = service.deactivate_source_for_user(
            source_id=source.id,
            user_id="hr-user-1",
            user_role="hr",
        )

        assert deactivated is True

        activated = service.activate_source_for_user(
            source_id=source.id,
            user_id="hr-user-1",
            user_role="hr",
        )

        assert activated is True

        rag_index = get_rag_index(db, "hr-user-1")

        assert rag_index is not None
        assert rag_index.status == RagIndexStatus.STALE.value
        assert rag_index.reindex_required is True
        assert rag_index.sources_count == 1
        assert rag_index.sources_hash is not None

    finally:
        db.close()


def test_permanent_delete_source_marks_user_rag_index_stale(tmp_path: Path) -> None:
    db = make_test_db()

    try:
        create_user(db, "hr-user-1")

        first_file = make_text_file(
            tmp_path=tmp_path,
            filename="first.txt",
            content="Первый источник: Python FastAPI.",
        )
        second_file = make_text_file(
            tmp_path=tmp_path,
            filename="second.txt",
            content="Второй источник: PostgreSQL Docker.",
        )

        service = RagSourceService(db)

        first_source = service.create_source_from_file(
            file_path=first_file,
            original_filename="first.txt",
            owner_user_id="hr-user-1",
            title="First source",
            source_type="vacancy",
        )
        service.create_source_from_file(
            file_path=second_file,
            original_filename="second.txt",
            owner_user_id="hr-user-1",
            title="Second source",
            source_type="vacancy",
        )

        deleted = service.permanently_delete_source_for_user(
            source_id=first_source.id,
            user_id="hr-user-1",
            user_role="hr",
        )

        assert deleted is True

        rag_index = get_rag_index(db, "hr-user-1")

        assert rag_index is not None
        assert rag_index.status == RagIndexStatus.STALE.value
        assert rag_index.reindex_required is True
        assert rag_index.sources_count == 1
        assert rag_index.sources_hash is not None

    finally:
        db.close()


def test_admin_changes_source_marks_real_owner_index_stale(tmp_path: Path) -> None:
    db = make_test_db()

    try:
        create_user(db, "hr-user-1")
        create_user(db, "admin-user").role = "admin"
        db.commit()

        file_path = make_text_file(
            tmp_path=tmp_path,
            filename="admin-visible.txt",
            content="Источник HR, который может администрировать admin.",
        )

        service = RagSourceService(db)

        source = service.create_source_from_file(
            file_path=file_path,
            original_filename="admin-visible.txt",
            owner_user_id="hr-user-1",
            title="Admin visible source",
            source_type="other",
        )

        deactivated = service.deactivate_source_for_user(
            source_id=source.id,
            user_id="admin-user",
            user_role="admin",
        )

        assert deactivated is True

        owner_index = get_rag_index(db, "hr-user-1")
        admin_index = get_rag_index(db, "admin-user")

        assert owner_index is not None
        assert owner_index.status == RagIndexStatus.STALE.value
        assert owner_index.reindex_required is True
        assert admin_index is None

    finally:
        db.close()
from pathlib import Path

from sqlalchemy import delete

from app.core.privacy import contains_personal_data
from app.db.models import RagSourceORM
from app.db.session import SessionLocal
from app.services.rag_source_service import RagSourceService


def test_rag_source_service_creates_text_source_and_masks_personal_data(
    tmp_path: Path,
) -> None:
    db = SessionLocal()
    file_path = tmp_path / "backend_vacancy.txt"
    file_path.write_text(
        "Вакансия Backend Python. "
        "Контакт: hr@example.com, телефон +7 999 123-45-67. "
        "Требования: Python, FastAPI, PostgreSQL, Docker.",
        encoding="utf-8",
    )

    try:
        service = RagSourceService(db)

        source = service.create_source_from_file(
            file_path=file_path,
            original_filename="hr@example.com_backend_vacancy.txt",
            owner_user_id="hr-user-1",
            title="Backend vacancy hr@example.com",
            source_type="vacancy",
        )

        assert source.id
        assert source.owner_user_id == "hr-user-1"
        assert source.source_type == "vacancy"
        assert source.source_format == "txt"
        assert source.is_active is True
        assert len(source.content_hash) == 64

        assert not contains_personal_data(source.filename)
        assert not contains_personal_data(source.title)
        assert not contains_personal_data(source.content)

        assert "FastAPI" in source.content
        assert "PostgreSQL" in source.content
        assert "Docker" in source.content

    finally:
        db.execute(delete(RagSourceORM).where(RagSourceORM.owner_user_id == "hr-user-1"))
        db.commit()
        db.close()


def test_rag_source_service_lists_only_own_sources_for_hr(
    tmp_path: Path,
) -> None:
    db = SessionLocal()

    first_file = tmp_path / "first.txt"
    second_file = tmp_path / "second.txt"

    first_file.write_text("Первый источник: Python FastAPI.", encoding="utf-8")
    second_file.write_text("Второй источник: Java Spring.", encoding="utf-8")

    try:
        service = RagSourceService(db)

        first_source = service.create_source_from_file(
            file_path=first_file,
            original_filename="first.txt",
            owner_user_id="hr-user-1",
            title="First source",
            source_type="vacancy",
        )

        second_source = service.create_source_from_file(
            file_path=second_file,
            original_filename="second.txt",
            owner_user_id="hr-user-2",
            title="Second source",
            source_type="vacancy",
        )

        hr_sources = service.list_sources_for_user(
            user_id="hr-user-1",
            user_role="hr",
        )

        hr_source_ids = {
            source.id
            for source in hr_sources
        }

        assert first_source.id in hr_source_ids
        assert second_source.id not in hr_source_ids

        admin_sources = service.list_sources_for_user(
            user_id="admin-user",
            user_role="admin",
        )

        admin_source_ids = {
            source.id
            for source in admin_sources
        }

        assert first_source.id in admin_source_ids
        assert second_source.id in admin_source_ids

    finally:
        db.execute(delete(RagSourceORM).where(RagSourceORM.owner_user_id.in_(
            [
                "hr-user-1",
                "hr-user-2",
            ]
        )))
        db.commit()
        db.close()


def test_rag_source_service_deactivates_source_for_owner(
    tmp_path: Path,
) -> None:
    db = SessionLocal()
    file_path = tmp_path / "policy.md"
    file_path.write_text("Корпоративный чек-лист проверки резюме.", encoding="utf-8")

    try:
        service = RagSourceService(db)

        source = service.create_source_from_file(
            file_path=file_path,
            original_filename="policy.md",
            owner_user_id="hr-user-1",
            title="CV policy",
            source_type="policy",
        )

        deleted = service.deactivate_source_for_user(
            source_id=source.id,
            user_id="hr-user-1",
            user_role="hr",
        )

        assert deleted is True

        db.refresh(source)

        assert source.is_active is False

        active_sources = service.list_sources_for_user(
            user_id="hr-user-1",
            user_role="hr",
        )

        assert source.id not in {
            item.id
            for item in active_sources
        }

        inactive_sources = service.list_sources_for_user(
            user_id="hr-user-1",
            user_role="hr",
            include_inactive=True,
        )

        assert source.id in {
            item.id
            for item in inactive_sources
        }

    finally:
        db.execute(delete(RagSourceORM).where(RagSourceORM.owner_user_id == "hr-user-1"))
        db.commit()
        db.close()


def test_rag_source_service_loads_sources_as_rag_sources(
    tmp_path: Path,
) -> None:
    db = SessionLocal()
    file_path = tmp_path / "requirements.txt"
    file_path.write_text(
        "Требования вакансии: Python, FastAPI, PostgreSQL.",
        encoding="utf-8",
    )

    try:
        service = RagSourceService(db)

        source = service.create_source_from_file(
            file_path=file_path,
            original_filename="requirements.txt",
            owner_user_id="hr-user-1",
            title="Backend requirements",
            source_type="requirements",
        )

        rag_sources = service.load_active_rag_sources_for_user(
            user_id="hr-user-1",
            user_role="hr",
        )

        matching_sources = [
            item
            for item in rag_sources
            if item.source_id == source.id
        ]

        assert len(matching_sources) == 1

        rag_source = matching_sources[0]

        assert rag_source.title == "Backend requirements"
        assert rag_source.path == f"db://rag_sources/{source.id}"
        assert "FastAPI" in rag_source.content

    finally:
        db.execute(delete(RagSourceORM).where(RagSourceORM.owner_user_id == "hr-user-1"))
        db.commit()
        db.close()
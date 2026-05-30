from datetime import datetime, timezone

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.coordinator.formal_check_coordinator import FormalCheckCoordinator
from app.db.models import (
    Base,
    CheckORM,
    DocumentORM,
    DocumentSectionORM,
    IssueORM,
    ProcessingSessionORM,
    RagIndexORM,
    RagSourceORM,
    RecommendationORM,
    ReportORM,
    UserORM,
)
from app.reports.report_builder import ReportBuilder
from app.schemas.common import DocumentType, ProcessingStatus, SourceFormat, StorageMode
from app.schemas.documents import DocumentMetadata, DocumentSection, ParsedDocument
from app.services.backup_service import BackupService
from app.services.report_storage_service import ReportStorageService


def make_test_document() -> ParsedDocument:
    return ParsedDocument(
        metadata=DocumentMetadata(
            document_id="backup-test-doc",
            document_type=DocumentType.CV,
            source_format=SourceFormat.DOCX,
            filename="resume.docx",
            upload_time=datetime.now(timezone.utc),
            processing_status=ProcessingStatus.PARSED,
            storage_mode=StorageMode.TEMPORARY,
        ),
        raw_text="Короткое резюме без контактов",
        sections=[
            DocumentSection(
                section_id="section-1",
                section_type="unknown",
                title=None,
                text="Короткое резюме без контактов",
                position_in_document=0,
            )
        ],
        entities=[],
    )


def make_session() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )

    Base.metadata.create_all(bind=engine)

    return SessionLocal()


def count_rows(db: Session, model: type[Base]) -> int:
    return db.execute(select(func.count()).select_from(model)).scalar_one()


def test_backup_service_exports_and_restores_normalized_schema() -> None:
    source_db = make_session()

    try:
        document = make_test_document()
        formal_check_response = FormalCheckCoordinator().run(document)

        report = ReportBuilder().build(
            document=document,
            formal_check_response=formal_check_response,
        )

        ReportStorageService(source_db).save_report(
            document=document,
            report=report,
            owner_user_id="user-1",
        )

        source_db.add(
            RagSourceORM(
                id="backup-rag-source-1",
                owner_user_id=None,
                title="Backup RAG source",
                filename="backup_rag_source.txt",
                source_type="requirements",
                source_format="txt",
                content="Требования: Python, FastAPI, PostgreSQL.",
                content_hash="hash-backup-rag-source-1",
                file_size_bytes=128,
                is_active=True,
                source_metadata={"content_length": 38},
            )
        )

        source_db.add(
            UserORM(
                id="backup-rag-index-user",
                email="backup-rag-index-user@example.test",
                full_name="Backup RAG Index User",
                role="hr",
                password_hash="test-password-hash",
                is_active=True,
            )
        )

        source_db.add(
            RagIndexORM(
                id="backup-rag-index-1",
                owner_user_id="backup-rag-index-user",
                status="ready",
                reindex_required=False,
                index_path="/app/data/index/users/backup-rag-index-user/faiss.index",
                chunks_path="/app/data/index/users/backup-rag-index-user/chunks.json",
                sources_hash="backup-rag-index-sources-hash",
                sources_count=1,
                chunks_count=3,
                embedding_backend="hashing",
                embedding_model_name="hashing",
                embedding_dimension=384,
                retriever_type="faiss",
                index_metadata={
                    "backup_test": True,
                },
                error_message=None,
            )
        )

        source_db.commit()

        backup_payload = BackupService(source_db).create_backup_payload()

        assert backup_payload["backup_version"] == "2.0"
        assert len(backup_payload["documents"]) == 1
        assert len(backup_payload["document_sections"]) == 1
        assert len(backup_payload["processing_sessions"]) == 1
        assert len(backup_payload["reports"]) == 1
        assert len(backup_payload["checks"]) > 0
        assert len(backup_payload["issues"]) > 0
        assert len(backup_payload["recommendations"]) > 0
        assert len(backup_payload["rag_sources"]) == 1
        assert len(backup_payload["rag_indexes"]) == 1

        assert backup_payload["documents"][0]["owner_user_id"] == "user-1"
        assert backup_payload["reports"][0]["owner_user_id"] == "user-1"
        assert backup_payload["processing_sessions"][0]["owner_user_id"] == "user-1"

        assert backup_payload["rag_sources"][0]["id"] == "backup-rag-source-1"
        assert backup_payload["rag_sources"][0]["owner_user_id"] is None
        assert backup_payload["rag_sources"][0]["file_size_bytes"] == 128
        assert backup_payload["rag_sources"][0]["is_active"] is True
        assert backup_payload["rag_indexes"][0]["id"] == "backup-rag-index-1"
        assert backup_payload["rag_indexes"][0]["owner_user_id"] == "backup-rag-index-user"
        assert backup_payload["rag_indexes"][0]["status"] == "ready"
        assert backup_payload["rag_indexes"][0]["reindex_required"] is False
        assert backup_payload["rag_indexes"][0]["chunks_count"] == 3

    finally:
        source_db.close()

    target_db = make_session()

    try:
        target_db.add(
            UserORM(
                id="backup-rag-index-user",
                email="backup-rag-index-user@example.test",
                full_name="Backup RAG Index User",
                role="hr",
                password_hash="test-password-hash",
                is_active=True,
            )
        )
        target_db.commit()

        result = BackupService(target_db).restore_from_payload(backup_payload)

        assert result["restored_documents"] == 1
        assert result["restored_document_sections"] == 1
        assert result["restored_processing_sessions"] == 1
        assert result["restored_reports"] == 1
        assert result["restored_checks"] == len(backup_payload["checks"])
        assert result["restored_issues"] == len(backup_payload["issues"])
        assert result["restored_recommendations"] == len(backup_payload["recommendations"])
        assert result["restored_rag_sources"] == 1
        assert result["restored_rag_indexes"] == 1

        assert count_rows(target_db, DocumentORM) == 1
        assert count_rows(target_db, DocumentSectionORM) == 1
        assert count_rows(target_db, ProcessingSessionORM) == 1
        assert count_rows(target_db, ReportORM) == 1
        assert count_rows(target_db, CheckORM) == len(backup_payload["checks"])
        assert count_rows(target_db, IssueORM) == len(backup_payload["issues"])
        assert count_rows(target_db, RecommendationORM) == len(
            backup_payload["recommendations"]
        )
        assert count_rows(target_db, RagSourceORM) == 1
        assert count_rows(target_db, RagIndexORM) == 1

        restored_payload = BackupService(target_db).create_backup_payload()

        assert restored_payload["documents"][0]["id"] == "backup-test-doc"
        assert restored_payload["documents"][0]["owner_user_id"] == "user-1"
        assert restored_payload["reports"][0]["owner_user_id"] == "user-1"
        assert restored_payload["processing_sessions"][0]["owner_user_id"] == "user-1"

        assert restored_payload["rag_sources"][0]["id"] == "backup-rag-source-1"
        assert restored_payload["rag_sources"][0]["owner_user_id"] is None
        assert restored_payload["rag_sources"][0]["file_size_bytes"] == 128

        assert restored_payload["rag_indexes"][0]["id"] == "backup-rag-index-1"
        assert restored_payload["rag_indexes"][0]["owner_user_id"] == "backup-rag-index-user"
        assert restored_payload["rag_indexes"][0]["status"] == "stale"
        assert restored_payload["rag_indexes"][0]["reindex_required"] is True
        assert restored_payload["rag_indexes"][0]["index_metadata"]["restored_from_backup"] is True

    finally:
        target_db.close()


def test_backup_restore_is_idempotent() -> None:
    source_db = make_session()

    try:
        document = make_test_document()
        formal_check_response = FormalCheckCoordinator().run(document)

        report = ReportBuilder().build(
            document=document,
            formal_check_response=formal_check_response,
        )

        ReportStorageService(source_db).save_report(
            document=document,
            report=report,
            owner_user_id="user-1",
        )

        backup_payload = BackupService(source_db).create_backup_payload()

    finally:
        source_db.close()

    target_db = make_session()

    try:
        first_result = BackupService(target_db).restore_from_payload(backup_payload)
        second_result = BackupService(target_db).restore_from_payload(backup_payload)

        assert first_result["restored_documents"] == 1
        assert first_result["restored_reports"] == 1
        assert first_result["restored_rag_sources"] == 0

        assert second_result["restored_documents"] == 0
        assert second_result["restored_document_sections"] == 0
        assert second_result["restored_processing_sessions"] == 0
        assert second_result["restored_reports"] == 0
        assert second_result["restored_checks"] == 0
        assert second_result["restored_issues"] == 0
        assert second_result["restored_recommendations"] == 0
        assert second_result["restored_rag_sources"] == 0

        assert count_rows(target_db, DocumentORM) == 1
        assert count_rows(target_db, ReportORM) == 1
        assert count_rows(target_db, RagSourceORM) == 0

        assert first_result["restored_rag_indexes"] == 0
        assert second_result["restored_rag_indexes"] == 0

    finally:
        target_db.close()
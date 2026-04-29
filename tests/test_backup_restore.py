from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.coordinator.formal_check_coordinator import FormalCheckCoordinator
from app.db.models import Base
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


def test_backup_service_exports_and_restores_data() -> None:
    source_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    SourceSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=source_engine,
    )

    Base.metadata.create_all(bind=source_engine)

    source_db = SourceSessionLocal()

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
        )

        backup_payload = BackupService(source_db).create_backup_payload()

        assert len(backup_payload["documents"]) == 1
        assert len(backup_payload["reports"]) == 1

    finally:
        source_db.close()

    target_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    TargetSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=target_engine,
    )

    Base.metadata.create_all(bind=target_engine)

    target_db = TargetSessionLocal()

    try:
        result = BackupService(target_db).restore_from_payload(backup_payload)

        assert result["restored_documents"] == 1
        assert result["restored_reports"] == 1

        restored_payload = BackupService(target_db).create_backup_payload()

        assert len(restored_payload["documents"]) == 1
        assert len(restored_payload["reports"]) == 1
        assert restored_payload["documents"][0]["id"] == "backup-test-doc"

    finally:
        target_db.close()
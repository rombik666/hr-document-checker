import json
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.coordinator.formal_check_coordinator import FormalCheckCoordinator
from app.db.models import Base
from app.reports.report_builder import ReportBuilder
from app.schemas.common import DocumentType, ProcessingStatus, SourceFormat, StorageMode
from app.schemas.documents import DocumentMetadata, DocumentSection, ParsedDocument
from app.services.report_storage_service import ReportStorageService


def test_saved_report_masks_personal_data() -> None:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )

    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()

    try:
        document = ParsedDocument(
            metadata=DocumentMetadata(
                document_id="test-doc",
                document_type=DocumentType.CV,
                source_format=SourceFormat.DOCX,
                filename="resume.docx",
                upload_time=datetime.now(timezone.utc),
                processing_status=ProcessingStatus.PARSED,
                storage_mode=StorageMode.TEMPORARY,
            ),
            raw_text="Email: ivan@example.com, телефон: +7 999 123-45-67",
            sections=[
                DocumentSection(
                    section_id="section-1",
                    section_type="unknown",
                    title=None,
                    text="Email: ivan@example.com, телефон: +7 999 123-45-67",
                    position_in_document=0,
                )
            ],
            entities=[],
        )

        formal_check_response = FormalCheckCoordinator().run(document)

        report = ReportBuilder().build(
            document=document,
            formal_check_response=formal_check_response,
        )

        # Искусственно добавляем evidence с ПДн,
        # чтобы проверить, что перед сохранением оно маскируется.
        if report.major:
            report.major[0].evidence_fragment = "ivan@example.com +7 999 123-45-67"
        elif report.minor:
            report.minor[0].evidence_fragment = "ivan@example.com +7 999 123-45-67"
        elif report.critical:
            report.critical[0].evidence_fragment = "ivan@example.com +7 999 123-45-67"

        service = ReportStorageService(db)

        service.save_report(
            document=document,
            report=report,
        )

        loaded_report = service.get_report(report.report_id)

        assert loaded_report is not None

        dumped = json.dumps(
            loaded_report.model_dump(mode="json"),
            ensure_ascii=False,
        )

        assert "ivan@example.com" not in dumped
        assert "+7 999 123-45-67" not in dumped
        assert "i***@example.com" in dumped
        assert "+7 *** ***-**-67" in dumped

    finally:
        db.close()
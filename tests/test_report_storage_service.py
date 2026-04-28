from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.coordinator.formal_check_coordinator import FormalCheckCoordinator
from app.db.models import Base
from app.reports.report_builder import ReportBuilder
from app.schemas.common import DocumentType, ProcessingStatus, SourceFormat, StorageMode
from app.schemas.documents import DocumentMetadata, DocumentSection, ParsedDocument
from app.services.report_storage_service import ReportStorageService


def test_report_storage_service_saves_and_loads_report() -> None:
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

        formal_check_response = FormalCheckCoordinator().run(document)

        report = ReportBuilder().build(
            document=document,
            formal_check_response=formal_check_response,
        )

        service = ReportStorageService(db)

        service.save_report(
            document=document,
            report=report,
        )

        loaded_report = service.get_report(report.report_id)

        assert loaded_report is not None
        assert loaded_report.report_id == report.report_id
        assert loaded_report.document_id == report.document_id
        assert loaded_report.filename == "resume.docx"
        assert loaded_report.total_issues == report.total_issues

    finally:
        db.close()
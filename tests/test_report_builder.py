from datetime import datetime, timezone

from app.coordinator.formal_check_coordinator import FormalCheckCoordinator
from app.reports.report_builder import ReportBuilder
from app.schemas.common import DocumentType, ProcessingStatus, ReportStatus, SourceFormat, StorageMode
from app.schemas.documents import DocumentMetadata, DocumentSection, ParsedDocument


def test_report_builder_groups_issues_by_severity() -> None:
    document = ParsedDocument(
        metadata=DocumentMetadata(
            document_id="test-doc",
            document_type=DocumentType.UNKNOWN,
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

    assert report.document_id == "test-doc"
    assert report.filename == "resume.docx"

    assert report.total_issues == formal_check_response.total_issues
    assert report.critical_count == formal_check_response.critical_count
    assert report.major_count == formal_check_response.major_count
    assert report.minor_count == formal_check_response.minor_count

    assert report.summary_status == ReportStatus.REQUIRES_REVISION
    assert report.technical_info.total_agents_count == 4
    assert "CompletenessAgent" in report.technical_info.checks_completed
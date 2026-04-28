from datetime import datetime, timezone

from app.coordinator.formal_check_coordinator import FormalCheckCoordinator
from app.reports.report_builder import ReportBuilder
from app.schemas.common import DocumentType, ProcessingStatus, ReportStatus, SourceFormat, StorageMode
from app.schemas.documents import DocumentMetadata, DocumentSection, ParsedDocument
from app.coordinator.semantic_check_coordinator import SemanticCheckCoordinator


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

    from app.coordinator.semantic_check_coordinator import SemanticCheckCoordinator


def test_report_builder_includes_semantic_results() -> None:
    document = ParsedDocument(
        metadata=DocumentMetadata(
            document_id="test-doc-semantic",
            document_type=DocumentType.CV,
            source_format=SourceFormat.DOCX,
            filename="resume.docx",
            upload_time=datetime.now(timezone.utc),
            processing_status=ProcessingStatus.PARSED,
            storage_mode=StorageMode.TEMPORARY,
        ),
        raw_text=(
            "Backend developer. "
            "Занимался разработкой backend. "
            "Навыки: Python, Git."
        ),
        sections=[
            DocumentSection(
                section_id="section-1",
                section_type="experience",
                title=None,
                text="Занимался разработкой backend.",
                position_in_document=0,
            )
        ],
        entities=[],
    )

    formal_check_response = FormalCheckCoordinator().run(document)

    semantic_check_response = SemanticCheckCoordinator().run(
        document=document,
        vacancy_text="Требования: Python, FastAPI, PostgreSQL, Docker, Git.",
    )

    report = ReportBuilder().build(
        document=document,
        formal_check_response=formal_check_response,
        semantic_check_response=semantic_check_response,
        vacancy_text="Требования: Python, FastAPI, PostgreSQL, Docker, Git.",
    )

    issue_types = {
        issue.issue_type
        for issue in report.critical + report.major + report.minor
    }

    assert "weak_phrase" in issue_types
    assert "vacancy_requirements_gap" in issue_types

    assert report.vacancy_relevance is not None
    assert report.vacancy_relevance.coverage_percent is not None
    assert "fastapi" in report.vacancy_relevance.missing_requirements

    assert report.technical_info.metadata["semantic_checks_enabled"] is True
    assert report.technical_info.metadata["vacancy_text_provided"] is True
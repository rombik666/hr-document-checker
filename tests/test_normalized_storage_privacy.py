import json
from datetime import datetime, timezone

from sqlalchemy import delete

from app.core.privacy import contains_personal_data
from app.db.models import (
    CheckORM,
    DocumentORM,
    DocumentSectionORM,
    IssueORM,
    ProcessingSessionORM,
    RecommendationORM,
    ReportORM,
)
from app.db.session import SessionLocal
from app.schemas.checks import AgentExecutionInfo, CheckResult, Issue, Recommendation
from app.schemas.common import (
    CheckStatus,
    CheckType,
    DocumentType,
    ProcessingStatus,
    ReportStatus,
    Severity,
    SourceFormat,
    StorageMode,
)
from app.schemas.documents import DocumentMetadata, DocumentSection, ParsedDocument
from app.schemas.reports import Report, TechnicalInfo
from app.services.report_storage_service import ReportStorageService


def _as_text(value) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def test_normalized_report_storage_masks_personal_data() -> None:
    db = SessionLocal()

    document_id = "privacy-doc-normalized"
    report_id = "privacy-report-normalized"
    owner_user_id = "privacy-owner"

    now = datetime.now(timezone.utc)

    try:
        db.execute(delete(DocumentORM).where(DocumentORM.id == document_id))
        db.commit()

        parsed_document = ParsedDocument(
            metadata=DocumentMetadata(
                document_id=document_id,
                document_type=DocumentType.CV,
                source_format=SourceFormat.DOCX,
                filename="ivan@example.com_+79991234567_resume.docx",
                upload_time=now,
                processing_status=ProcessingStatus.REPORT_GENERATED,
                storage_mode=StorageMode.TEMPORARY,
            ),
            raw_text=(
                "Email: ivan@example.com. "
                "Телефон: +7 999 123-45-67."
            ),
            sections=[
                DocumentSection(
                    section_id="contacts",
                    section_type="contacts",
                    title="Контакты ivan@example.com",
                    text=(
                        "Email: ivan@example.com. "
                        "Телефон: +7 999 123-45-67."
                    ),
                    position_in_document=0,
                    metadata={
                        "source": "ivan@example.com",
                        "phone": "+7 999 123-45-67",
                    },
                )
            ],
        )

        issue = Issue(
            issue_id="issue-1",
            severity=Severity.MAJOR,
            issue_type="privacy_fixture",
            description="Проверьте контакт ivan@example.com.",
            evidence_fragment="Телефон кандидата: +7 999 123-45-67.",
            source_agent="PrivacyFixtureAgent",
            confidence_score=0.95,
            metadata={
                "email": "ivan@example.com",
                "phone": "+7 999 123-45-67",
            },
            recommendation=Recommendation(
                recommendation_id="rec-1",
                recommendation_text="Уточнить данные у ivan@example.com.",
                example_fix="Связаться по +7 999 123-45-67.",
                priority_order=1,
            ),
        )

        check_result = CheckResult(
            execution=AgentExecutionInfo(
                check_id="check-1",
                agent_name="PrivacyFixtureAgent",
                check_type=CheckType.SEMANTIC,
                status=CheckStatus.SUCCESS,
                started_at=now,
                ended_at=now,
                duration_ms=1.0,
                model_or_ruleset_version="privacy-fixture",
                error_message="debug ivan@example.com +7 999 123-45-67",
            ),
            issues=[issue],
        )

        report = Report(
            report_id=report_id,
            document_id=document_id,
            filename="ivan@example.com_+79991234567_resume.docx",
            summary_status=ReportStatus.REQUIRES_REVISION,
            summary="Найден контакт ivan@example.com и телефон +7 999 123-45-67.",
            total_issues=1,
            critical_count=0,
            major_count=1,
            minor_count=0,
            critical=[],
            major=[issue],
            minor=[],
            vacancy_relevance=None,
            technical_info=TechnicalInfo(
                generated_at=now,
                checks_completed=["PrivacyFixtureAgent"],
                failed_checks=[],
                ruleset_versions=["privacy-fixture"],
                total_agents_count=1,
                successful_agents_count=1,
                failed_agents_count=0,
                parser_warnings=[],
                metadata={
                    "filename": "ivan@example.com_+79991234567_resume.docx",
                },
            ),
            raw_check_results=[check_result],
        )

        assert contains_personal_data(parsed_document.sections[0].text)
        assert contains_personal_data(issue.evidence_fragment or "")

        ReportStorageService(db).save_report(
            document=parsed_document,
            report=report,
            owner_user_id=owner_user_id,
        )

        stored_document = db.get(DocumentORM, document_id)
        stored_report = db.get(ReportORM, report_id)
        stored_sections = (
            db.query(DocumentSectionORM)
            .filter(DocumentSectionORM.document_id == document_id)
            .all()
        )
        stored_sessions = (
            db.query(ProcessingSessionORM)
            .filter(ProcessingSessionORM.document_id == document_id)
            .all()
        )
        stored_checks = (
            db.query(CheckORM)
            .filter(CheckORM.document_id == document_id)
            .all()
        )
        stored_issues = (
            db.query(IssueORM)
            .filter(IssueORM.document_id == document_id)
            .all()
        )
        stored_recommendations = (
            db.query(RecommendationORM)
            .join(IssueORM, RecommendationORM.issue_id == IssueORM.id)
            .filter(IssueORM.document_id == document_id)
            .all()
        )

        fragments = [
            stored_document.filename,
            stored_report.filename,
            stored_report.summary,
            _as_text(stored_report.report_json),
            *[
                section.title or ""
                for section in stored_sections
            ],
            *[
                section.text
                for section in stored_sections
            ],
            *[
                _as_text(section.section_metadata)
                for section in stored_sections
            ],
            *[
                _as_text(session.session_metadata)
                for session in stored_sessions
            ],
            *[
                check.error_message or ""
                for check in stored_checks
            ],
            *[
                issue.description
                for issue in stored_issues
            ],
            *[
                issue.evidence_fragment or ""
                for issue in stored_issues
            ],
            *[
                _as_text(issue.issue_metadata)
                for issue in stored_issues
            ],
            *[
                recommendation.recommendation_text
                for recommendation in stored_recommendations
            ],
            *[
                recommendation.example_fix or ""
                for recommendation in stored_recommendations
            ],
        ]

        for fragment in fragments:
            assert not contains_personal_data(fragment), fragment

    finally:
        db.execute(delete(DocumentORM).where(DocumentORM.id == document_id))
        db.commit()
        db.close()
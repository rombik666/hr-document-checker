from datetime import datetime, timezone

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.db.models import (
    Base,
    CheckORM,
    DocumentORM,
    DocumentSectionORM,
    IssueORM,
    ProcessingSessionORM,
    RecommendationORM,
    ReportORM,
)
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


def make_test_document() -> ParsedDocument:
    now = datetime.now(timezone.utc)

    return ParsedDocument(
        metadata=DocumentMetadata(
            document_id="normalized-doc",
            document_type=DocumentType.CV,
            source_format=SourceFormat.DOCX,
            filename="resume.docx",
            upload_time=now,
            processing_status=ProcessingStatus.PARSED,
            storage_mode=StorageMode.TEMPORARY,
        ),
        raw_text="Контакты отсутствуют. Опыт работы: Python developer.",
        sections=[
            DocumentSection(
                section_id="section-1",
                section_type="experience",
                title="Опыт работы",
                text="Опыт работы: Python developer.",
                position_in_document=0,
            )
        ],
        entities=[],
    )


def make_test_report(report_id: str) -> Report:
    now = datetime.now(timezone.utc)

    recommendation = Recommendation(
        recommendation_id="rec-1",
        recommendation_text="Добавить e-mail и телефон в раздел контактов.",
        example_fix="Email: candidate@example.com, Телефон: +7 999 123-45-67",
        priority_order=1,
    )

    issue = Issue(
        issue_id="issue-1",
        severity=Severity.CRITICAL,
        issue_type="missing_contacts",
        description="В документе отсутствуют контактные данные.",
        evidence_fragment="Контакты отсутствуют.",
        recommendation=recommendation,
        source_agent="completeness_agent",
        confidence_score=0.95,
    )

    check_result = CheckResult(
        execution=AgentExecutionInfo(
            check_id="check-1",
            agent_name="completeness_agent",
            check_type=CheckType.FORMAL,
            status=CheckStatus.SUCCESS,
            started_at=now,
            ended_at=now,
            duration_ms=1.5,
            model_or_ruleset_version="ruleset-1.0.0",
        ),
        issues=[issue],
    )

    return Report(
        report_id=report_id,
        document_id="normalized-doc",
        filename="resume.docx",
        summary_status=ReportStatus.REQUIRES_REVISION,
        summary="Документ требует доработки.",
        total_issues=1,
        critical_count=1,
        major_count=0,
        minor_count=0,
        critical=[issue],
        major=[],
        minor=[],
        vacancy_relevance=None,
        technical_info=TechnicalInfo(
            generated_at=now,
            checks_completed=["completeness_agent"],
            failed_checks=[],
            ruleset_versions=["ruleset-1.0.0"],
            total_agents_count=1,
            successful_agents_count=1,
            failed_agents_count=0,
        ),
        raw_check_results=[check_result],
    )


def make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    session_local = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    Base.metadata.create_all(bind=engine)
    return session_local()


def count_rows(db, model) -> int:
    return db.execute(select(func.count()).select_from(model)).scalar_one()


def test_report_storage_persists_normalized_entities() -> None:
    db = make_session()

    try:
        document = make_test_document()
        report = make_test_report("normalized-report-1")

        ReportStorageService(db).save_report(
            document=document,
            report=report,
            owner_user_id="user-1",
        )

        assert count_rows(db, DocumentORM) == 1
        assert count_rows(db, DocumentSectionORM) == 1
        assert count_rows(db, ProcessingSessionORM) == 1
        assert count_rows(db, ReportORM) == 1
        assert count_rows(db, CheckORM) == 1
        assert count_rows(db, IssueORM) == 1
        assert count_rows(db, RecommendationORM) == 1

        saved_report = db.get(ReportORM, "normalized-report-1")
        assert saved_report is not None
        assert saved_report.processing_session_id == "session-normalized-report-1"
        assert saved_report.owner_user_id == "user-1"

        saved_issue = db.execute(select(IssueORM)).scalar_one()
        assert saved_issue.issue_type == "missing_contacts"
        assert saved_issue.severity == "Critical"

    finally:
        db.close()


def test_report_storage_allows_multiple_reports_for_same_document() -> None:
    db = make_session()

    try:
        document = make_test_document()
        storage = ReportStorageService(db)

        storage.save_report(
            document=document,
            report=make_test_report("normalized-report-1"),
            owner_user_id="user-1",
        )

        storage.save_report(
            document=document,
            report=make_test_report("normalized-report-2"),
            owner_user_id="user-1",
        )

        assert count_rows(db, DocumentORM) == 1
        assert count_rows(db, DocumentSectionORM) == 1
        assert count_rows(db, ProcessingSessionORM) == 2
        assert count_rows(db, ReportORM) == 2
        assert count_rows(db, CheckORM) == 2
        assert count_rows(db, IssueORM) == 2
        assert count_rows(db, RecommendationORM) == 2

    finally:
        db.close()
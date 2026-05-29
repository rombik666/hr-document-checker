from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import (
    CheckORM,
    DocumentORM,
    DocumentSectionORM,
    IssueORM,
    ProcessingSessionORM,
    RecommendationORM,
    ReportORM,
)
from app.schemas.checks import CheckResult, Issue
from app.schemas.documents import ParsedDocument
from app.schemas.reports import Report
from app.services.report_sanitizer_service import ReportSanitizerService


class ReportStorageService:
    """
    Сервис сохранения и получения отчётов из БД.

    В БД сохраняется маскированная версия отчёта,
    чтобы не хранить email/телефоны в долгосрочном хранилище.

    Дополнительно данные отчёта раскладываются по нормализованным
    таблицам: processing_sessions, checks, issues, recommendations.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.sanitizer = ReportSanitizerService()

    def user_can_access_report(
        self,
        report_id: str,
        user_id: str,
        user_role: str,
    ) -> bool:
        report = self.get_report_orm(report_id)

        if report is None:
            return False

        if user_role == "admin":
            return True

        return report.owner_user_id == user_id

    def get_report_orm(self, report_id: str) -> ReportORM | None:
        return self.db.get(ReportORM, report_id)

    def save_report(
        self,
        document: ParsedDocument,
        report: Report,
        owner_user_id: str | None = None,
    ) -> Report:
        """
        Сохраняет метаданные документа, маскированный JSON отчёта
        и нормализованные результаты проверок.
        """

        document_orm = self._upsert_document(
            document=document,
            owner_user_id=owner_user_id,
        )

        self._replace_document_sections(document)

        sanitized_report = self.sanitizer.sanitize(report)

        processing_session = self._create_processing_session(
            document=document,
            report=report,
            owner_user_id=owner_user_id,
        )

        report_orm = ReportORM(
            id=report.report_id,
            owner_user_id=owner_user_id,
            document_id=document_orm.id,
            processing_session_id=processing_session.id,
            filename=report.filename,
            summary_status=report.summary_status.value,
            total_issues=report.total_issues,
            critical_count=report.critical_count,
            major_count=report.major_count,
            minor_count=report.minor_count,
            summary=report.summary,
            report_json=sanitized_report.model_dump(mode="json"),
        )

        try:
            self.db.add(report_orm)
            self.db.flush()

            self._save_check_results(
                document=document,
                report=report,
                processing_session_id=processing_session.id,
            )

            self.db.commit()

        except Exception:
            self.db.rollback()
            raise

        return report

    def _upsert_document(
        self,
        document: ParsedDocument,
        owner_user_id: str | None,
    ) -> DocumentORM:
        existing_document = self.db.get(DocumentORM, document.metadata.document_id)

        if existing_document is not None:
            if existing_document.owner_user_id is None and owner_user_id is not None:
                existing_document.owner_user_id = owner_user_id

            existing_document.filename = document.metadata.filename
            existing_document.document_type = document.metadata.document_type.value
            existing_document.source_format = document.metadata.source_format.value
            existing_document.processing_status = document.metadata.processing_status.value
            existing_document.storage_mode = document.metadata.storage_mode.value

            return existing_document

        document_orm = DocumentORM(
            id=document.metadata.document_id,
            owner_user_id=owner_user_id,
            filename=document.metadata.filename,
            document_type=document.metadata.document_type.value,
            source_format=document.metadata.source_format.value,
            processing_status=document.metadata.processing_status.value,
            storage_mode=document.metadata.storage_mode.value,
        )

        self.db.add(document_orm)
        self.db.flush()

        return document_orm

    def _replace_document_sections(self, document: ParsedDocument) -> None:
        """
        Секции документа пересохраняются как актуальное представление
        последнего парсинга документа.
        """

        self.db.execute(
            delete(DocumentSectionORM).where(
                DocumentSectionORM.document_id == document.metadata.document_id
            )
        )

        for section in document.sections:
            section_id = f"{document.metadata.document_id}:{section.section_id}"

            self.db.add(
                DocumentSectionORM(
                    id=section_id,
                    document_id=document.metadata.document_id,
                    section_type=section.section_type,
                    title=section.title,
                    text=section.text,
                    position_in_document=section.position_in_document,
                    section_metadata={
                        **section.metadata,
                        "original_section_id": section.section_id,
                    },
                )
            )

    def _create_processing_session(
        self,
        document: ParsedDocument,
        report: Report,
        owner_user_id: str | None,
    ) -> ProcessingSessionORM:
        now = datetime.now(timezone.utc)

        processing_session = ProcessingSessionORM(
            id=f"session-{report.report_id}",
            document_id=document.metadata.document_id,
            owner_user_id=owner_user_id,
            status="completed",
            started_at=report.technical_info.generated_at,
            ended_at=now,
            duration_ms=None,
            session_metadata={
                "report_id": report.report_id,
                "filename": report.filename,
                "vacancy_relevance_present": report.vacancy_relevance is not None,
                "total_agents_count": report.technical_info.total_agents_count,
                "successful_agents_count": report.technical_info.successful_agents_count,
                "failed_agents_count": report.technical_info.failed_agents_count,
            },
        )

        self.db.add(processing_session)
        self.db.flush()

        return processing_session

    def _save_check_results(
        self,
        document: ParsedDocument,
        report: Report,
        processing_session_id: str,
    ) -> None:
        check_results = report.raw_check_results

        if not check_results:
            self._save_report_level_issues(
                document=document,
                report=report,
                processing_session_id=processing_session_id,
            )
            return

        for check_result in check_results:
            self._save_check_result(
                document=document,
                report=report,
                processing_session_id=processing_session_id,
                check_result=check_result,
            )

    def _save_check_result(
        self,
        document: ParsedDocument,
        report: Report,
        processing_session_id: str,
        check_result: CheckResult,
    ) -> None:
        execution = check_result.execution
        check_id = f"{report.report_id}:{execution.check_id}"

        check_orm = CheckORM(
            id=check_id,
            processing_session_id=processing_session_id,
            document_id=document.metadata.document_id,
            report_id=report.report_id,
            agent_name=execution.agent_name,
            check_type=execution.check_type.value,
            status=execution.status.value,
            started_at=execution.started_at,
            ended_at=execution.ended_at,
            duration_ms=execution.duration_ms,
            model_or_ruleset_version=execution.model_or_ruleset_version,
            error_message=execution.error_message,
        )

        self.db.add(check_orm)
        self.db.flush()

        for issue in check_result.issues:
            self._save_issue(
                document=document,
                report=report,
                check_id=check_id,
                issue=issue,
            )

    def _save_report_level_issues(
        self,
        document: ParsedDocument,
        report: Report,
        processing_session_id: str,
    ) -> None:
        """
        Резервный вариант: если raw_check_results пустой,
        сохраняем issues из итоговых списков отчёта.
        """

        now = datetime.now(timezone.utc)
        check_id = f"{report.report_id}:report-level-issues"

        self.db.add(
            CheckORM(
                id=check_id,
                processing_session_id=processing_session_id,
                document_id=document.metadata.document_id,
                report_id=report.report_id,
                agent_name="report_builder",
                check_type="semantic",
                status="success",
                started_at=now,
                ended_at=now,
                duration_ms=0.0,
                model_or_ruleset_version="report-builder",
                error_message=None,
            )
        )

        self.db.flush()

        for issue in [*report.critical, *report.major, *report.minor]:
            self._save_issue(
                document=document,
                report=report,
                check_id=check_id,
                issue=issue,
            )

    def _save_issue(
        self,
        document: ParsedDocument,
        report: Report,
        check_id: str,
        issue: Issue,
    ) -> None:
        issue_id = f"{report.report_id}:{issue.issue_id}"

        issue_orm = IssueORM(
            id=issue_id,
            check_id=check_id,
            document_id=document.metadata.document_id,
            report_id=report.report_id,
            severity=issue.severity.value,
            issue_type=issue.issue_type,
            description=issue.description,
            evidence_fragment=issue.evidence_fragment,
            source_agent=issue.source_agent,
            confidence_score=issue.confidence_score,
            issue_metadata={
                **issue.metadata,
                "original_issue_id": issue.issue_id,
            },
        )

        self.db.add(issue_orm)
        self.db.flush()

        if issue.recommendation is None:
            return

        recommendation = issue.recommendation
        recommendation_id = f"{report.report_id}:{recommendation.recommendation_id}"

        self.db.add(
            RecommendationORM(
                id=recommendation_id,
                issue_id=issue_id,
                recommendation_text=recommendation.recommendation_text,
                example_fix=recommendation.example_fix,
                priority_order=recommendation.priority_order,
            )
        )

    def get_report(self, report_id: str) -> Report | None:
        """
        Получает сохранённый отчёт по report_id.
        """

        report_orm = self.db.get(ReportORM, report_id)

        if report_orm is None:
            return None

        return Report.model_validate(report_orm.report_json)

    def list_report_records_for_user(
        self,
        user_id: str,
        user_role: str,
        limit: int = 20,
    ) -> list[ReportORM]:
        statement = (
            select(ReportORM)
            .order_by(ReportORM.created_at.desc())
            .limit(limit)
        )

        if user_role != "admin":
            statement = statement.where(ReportORM.owner_user_id == user_id)

        return list(self.db.execute(statement).scalars().all())
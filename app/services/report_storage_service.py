from sqlalchemy.orm import Session

from app.db.models import DocumentORM, ReportORM
from app.schemas.documents import ParsedDocument
from app.schemas.reports import Report
from app.services.report_sanitizer_service import ReportSanitizerService


class ReportStorageService:
    """
    Сервис сохранения и получения отчётов из БД.

    В БД сохраняется маскированная версия отчёта,
    чтобы не хранить email/телефоны в долгосрочном хранилище.
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
        Сохраняет метаданные документа и маскированный JSON отчёта.
        """

        existing_document = self.db.get(DocumentORM, document.metadata.document_id)

        if existing_document is None:
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

        sanitized_report = self.sanitizer.sanitize(report)

        report_orm = ReportORM(
            id=report.report_id,
            owner_user_id=owner_user_id,
            document_id=document.metadata.document_id,
            filename=report.filename,
            summary_status=report.summary_status.value,
            total_issues=report.total_issues,
            critical_count=report.critical_count,
            major_count=report.major_count,
            minor_count=report.minor_count,
            summary=report.summary,
            report_json=sanitized_report.model_dump(mode="json"),
        )

        self.db.add(document_orm)
        self.db.add(report_orm)
        self.db.commit()

        return report

    def get_report(self, report_id: str) -> Report | None:
        """
        Получает сохранённый отчёт по report_id.
        """

        report_orm = self.db.get(ReportORM, report_id)

        if report_orm is None:
            return None

        return Report.model_validate(report_orm.report_json)
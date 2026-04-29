from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import DocumentORM, ReportORM


class BackupService:
    """
    Сервис резервного копирования и восстановления.

    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def create_backup_payload(self) -> dict[str, Any]:
        documents = self.db.query(DocumentORM).all()
        reports = self.db.query(ReportORM).all()

        return {
            "backup_version": "1.0",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "documents": [
                {
                    "id": document.id,
                    "filename": document.filename,
                    "document_type": document.document_type,
                    "source_format": document.source_format,
                    "processing_status": document.processing_status,
                    "storage_mode": document.storage_mode,
                    "created_at": document.created_at.isoformat()
                    if document.created_at
                    else None,
                }
                for document in documents
            ],
            "reports": [
                {
                    "id": report.id,
                    "document_id": report.document_id,
                    "filename": report.filename,
                    "summary_status": report.summary_status,
                    "total_issues": report.total_issues,
                    "critical_count": report.critical_count,
                    "major_count": report.major_count,
                    "minor_count": report.minor_count,
                    "summary": report.summary,
                    "report_json": report.report_json,
                    "created_at": report.created_at.isoformat()
                    if report.created_at
                    else None,
                }
                for report in reports
            ],
        }

    def restore_from_payload(self, payload: dict[str, Any]) -> dict[str, int]:
        """
        Восстанавливает документы и отчёты.

        Если запись с таким id уже есть, она не дублируется.
        """

        restored_documents = 0
        restored_reports = 0

        for document_data in payload.get("documents", []):
            document_id = document_data["id"]

            existing_document = self.db.get(DocumentORM, document_id)

            if existing_document is not None:
                continue

            document = DocumentORM(
                id=document_id,
                filename=document_data["filename"],
                document_type=document_data["document_type"],
                source_format=document_data["source_format"],
                processing_status=document_data["processing_status"],
                storage_mode=document_data["storage_mode"],
            )

            self.db.add(document)
            restored_documents += 1

        self.db.flush()

        for report_data in payload.get("reports", []):
            report_id = report_data["id"]

            existing_report = self.db.get(ReportORM, report_id)

            if existing_report is not None:
                continue

            report = ReportORM(
                id=report_id,
                document_id=report_data["document_id"],
                filename=report_data["filename"],
                summary_status=report_data["summary_status"],
                total_issues=report_data["total_issues"],
                critical_count=report_data["critical_count"],
                major_count=report_data["major_count"],
                minor_count=report_data["minor_count"],
                summary=report_data["summary"],
                report_json=report_data["report_json"],
            )

            self.db.add(report)
            restored_reports += 1

        self.db.commit()

        return {
            "restored_documents": restored_documents,
            "restored_reports": restored_reports,
        }
import json
import re
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import DocumentORM, ReportORM


EMAIL_PATTERN = re.compile(
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
)

PHONE_PATTERN = re.compile(
    r"(?:\+7|8)[\s\-()]?\d{3}[\s\-()]?\d{3}[\s\-()]?\d{2}[\s\-()]?\d{2}",
)


class DbInspectionService:

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_database_status(self) -> dict[str, Any]:
        documents_count = self.db.query(DocumentORM).count()
        reports_count = self.db.query(ReportORM).count()

        return {
            "database_available": True,
            "documents_count": documents_count,
            "reports_count": reports_count,
            "raw_text_column_exists": self._raw_text_column_exists(),
            "pii_masking_expected": True,
            "long_term_storage_contains_source_files": False,
        }

    def run_privacy_check(self) -> dict[str, Any]:
        reports = self.db.query(ReportORM).all()

        checked_reports = 0
        reports_with_unmasked_email = []
        reports_with_unmasked_phone = []

        for report in reports:
            checked_reports += 1

            report_text = self._report_json_to_text(report.report_json)

            if EMAIL_PATTERN.search(report_text):
                reports_with_unmasked_email.append(report.id)

            if PHONE_PATTERN.search(report_text):
                reports_with_unmasked_phone.append(report.id)

        passed = (
            not reports_with_unmasked_email
            and not reports_with_unmasked_phone
            and not self._raw_text_column_exists()
        )

        return {
            "passed": passed,
            "checked_reports": checked_reports,
            "raw_text_column_exists": self._raw_text_column_exists(),
            "reports_with_unmasked_email": reports_with_unmasked_email,
            "reports_with_unmasked_phone": reports_with_unmasked_phone,
            "unmasked_email_count": len(reports_with_unmasked_email),
            "unmasked_phone_count": len(reports_with_unmasked_phone),
        }

    @staticmethod
    def _report_json_to_text(report_json: Any) -> str:
        if report_json is None:
            return ""

        if isinstance(report_json, str):
            return report_json

        return json.dumps(
            report_json,
            ensure_ascii=False,
            default=str,
        )

    @staticmethod
    def _raw_text_column_exists() -> bool:
        document_columns = {
            column.name
            for column in DocumentORM.__table__.columns
        }

        report_columns = {
            column.name
            for column in ReportORM.__table__.columns
        }

        return "raw_text" in document_columns or "raw_text" in report_columns
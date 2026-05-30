import json
from typing import Any

from sqlalchemy.orm import Session

from app.core.privacy import EMAIL_PATTERN, PHONE_PATTERN
from app.db.models import (
    CheckORM,
    DocumentORM,
    DocumentSectionORM,
    IssueORM,
    ProcessingSessionORM,
    RecommendationORM,
    ReportORM,
)


class DbInspectionService:

    INSPECTED_FIELDS = [
        (
            DocumentORM,
            "documents",
            [
                "filename",
            ],
        ),
        (
            DocumentSectionORM,
            "document_sections",
            [
                "title",
                "text",
                "section_metadata",
            ],
        ),
        (
            ProcessingSessionORM,
            "processing_sessions",
            [
                "session_metadata",
            ],
        ),
        (
            ReportORM,
            "reports",
            [
                "filename",
                "summary",
                "report_json",
            ],
        ),
        (
            CheckORM,
            "checks",
            [
                "error_message",
            ],
        ),
        (
            IssueORM,
            "issues",
            [
                "description",
                "evidence_fragment",
                "issue_metadata",
            ],
        ),
        (
            RecommendationORM,
            "recommendations",
            [
                "recommendation_text",
                "example_fix",
            ],
        ),
    ]

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

        findings: list[dict[str, str]] = []
        checked_tables: list[str] = []
        checked_records = 0

        reports_with_unmasked_email: set[str] = set()
        reports_with_unmasked_phone: set[str] = set()

        for model, table_name, field_names in self.INSPECTED_FIELDS:
            checked_tables.append(table_name)

            records = self.db.query(model).all()
            checked_records += len(records)

            for record in records:
                record_id = str(getattr(record, "id", ""))

                for field_name in field_names:
                    value = getattr(record, field_name, None)
                    text_value = self._value_to_text(value)

                    if not text_value:
                        continue

                    has_email = bool(EMAIL_PATTERN.search(text_value))
                    has_phone = bool(PHONE_PATTERN.search(text_value))

                    if has_email:
                        findings.append(
                            {
                                "table_name": table_name,
                                "column_name": field_name,
                                "record_id": record_id,
                                "finding_type": "email",
                            }
                        )

                        if table_name == "reports":
                            reports_with_unmasked_email.add(record_id)

                    if has_phone:
                        findings.append(
                            {
                                "table_name": table_name,
                                "column_name": field_name,
                                "record_id": record_id,
                                "finding_type": "phone",
                            }
                        )

                        if table_name == "reports":
                            reports_with_unmasked_phone.add(record_id)

        raw_text_column_exists = self._raw_text_column_exists()

        unmasked_email_count = sum(
            1
            for finding in findings
            if finding["finding_type"] == "email"
        )
        unmasked_phone_count = sum(
            1
            for finding in findings
            if finding["finding_type"] == "phone"
        )

        passed = (
            not findings
            and not raw_text_column_exists
        )

        return {
            "passed": passed,
            "checked_reports": self.db.query(ReportORM).count(),
            "checked_tables": checked_tables,
            "checked_records": checked_records,
            "raw_text_column_exists": raw_text_column_exists,
            "reports_with_unmasked_email": sorted(reports_with_unmasked_email),
            "reports_with_unmasked_phone": sorted(reports_with_unmasked_phone),
            "unmasked_email_count": unmasked_email_count,
            "unmasked_phone_count": unmasked_phone_count,
            "findings": findings,
        }

    @staticmethod
    def _value_to_text(value: Any) -> str:
        if value is None:
            return ""

        if isinstance(value, str):
            return value

        return json.dumps(
            value,
            ensure_ascii=False,
            default=str,
        )

    @classmethod
    def _raw_text_column_exists(cls) -> bool:
        inspected_models = [
            DocumentORM,
            DocumentSectionORM,
            ProcessingSessionORM,
            ReportORM,
            CheckORM,
            IssueORM,
            RecommendationORM,
        ]

        for model in inspected_models:
            column_names = {
                column.name
                for column in model.__table__.columns
            }

            if "raw_text" in column_names:
                return True

        return False
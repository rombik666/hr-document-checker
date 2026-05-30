from typing import Any

from app.core.privacy import mask_text
from app.schemas.reports import Report


class ReportSanitizerService:
    """
    Сервис маскирования персональных данных в отчёте и вложенных структурах.
    """

    def sanitize(self, report: Report) -> Report:
        report_data = report.model_dump(mode="json")
        sanitized_data = self.sanitize_value(report_data)

        return Report.model_validate(sanitized_data)

    def sanitize_value(self, value: Any) -> Any:
        if isinstance(value, str):
            return mask_text(value)

        if isinstance(value, list):
            return [
                self.sanitize_value(item)
                for item in value
            ]

        if isinstance(value, dict):
            return {
                key: self.sanitize_value(item)
                for key, item in value.items()
            }

        return value
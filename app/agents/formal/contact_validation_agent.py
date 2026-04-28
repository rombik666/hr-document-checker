from uuid import uuid4

from app.agents.formal.base import BaseFormalAgent
from app.schemas.checks import Issue, Recommendation
from app.schemas.common import EntityType, Severity
from app.schemas.documents import ParsedDocument


class ContactValidationAgent(BaseFormalAgent):
    """
    Агент проверки контактных данных.

    """

    agent_name = "ContactValidationAgent"

    def check(self, document: ParsedDocument) -> list[Issue]:
        issues: list[Issue] = []

        emails = [
            entity for entity in document.entities
            if entity.entity_type == EntityType.EMAIL
        ]

        phones = [
            entity for entity in document.entities
            if entity.entity_type == EntityType.PHONE
        ]

        normalized_emails = [
            entity.normalized_value or entity.value.lower()
            for entity in emails
        ]

        normalized_phones = [
            entity.normalized_value or entity.value
            for entity in phones
        ]

        if len(normalized_emails) != len(set(normalized_emails)):
            issues.append(
                self._make_issue(
                    severity=Severity.MINOR,
                    issue_type="duplicated_email",
                    description="В документе найден повторяющийся e-mail.",
                    recommendation_text="Оставьте один актуальный e-mail, чтобы не перегружать блок контактов.",
                )
            )

        if len(normalized_phones) != len(set(normalized_phones)):
            issues.append(
                self._make_issue(
                    severity=Severity.MINOR,
                    issue_type="duplicated_phone",
                    description="В документе найден повторяющийся номер телефона.",
                    recommendation_text="Оставьте один актуальный номер телефона.",
                )
            )

        for phone in phones:
            normalized = phone.normalized_value or ""

            digits_count = sum(char.isdigit() for char in normalized)

            if digits_count < 10:
                issues.append(
                    self._make_issue(
                        severity=Severity.MAJOR,
                        issue_type="invalid_phone",
                        description=f"Номер телефона выглядит неполным: {phone.value}",
                        recommendation_text="Проверьте номер телефона и укажите его полностью.",
                        evidence_fragment=phone.value,
                    )
                )

        return issues

    def _make_issue(
        self,
        severity: Severity,
        issue_type: str,
        description: str,
        recommendation_text: str,
        evidence_fragment: str | None = None,
    ) -> Issue:
        return Issue(
            issue_id=str(uuid4()),
            severity=severity,
            issue_type=issue_type,
            description=description,
            evidence_fragment=evidence_fragment,
            recommendation=Recommendation(
                recommendation_id=str(uuid4()),
                recommendation_text=recommendation_text,
            ),
            source_agent=self.agent_name,
            confidence_score=0.85,
        )
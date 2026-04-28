from uuid import uuid4

from app.agents.formal.base import BaseFormalAgent
from app.schemas.checks import Issue, Recommendation
from app.schemas.common import EntityType, Severity
from app.schemas.documents import ParsedDocument


class DatePresenceAgent(BaseFormalAgent):
    """
    Агент проверки дат.

    """

    agent_name = "DatePresenceAgent"

    def check(self, document: ParsedDocument) -> list[Issue]:
        issues: list[Issue] = []

        has_experience_section = any(
            section.section_type == "experience"
            for section in document.sections
        )

        dates = [
            entity for entity in document.entities
            if entity.entity_type == EntityType.DATE
        ]

        if has_experience_section and not dates:
            experience_section = next(
                section for section in document.sections
                if section.section_type == "experience"
            )

            issues.append(
                self._make_issue(
                    severity=Severity.MAJOR,
                    issue_type="missing_experience_dates",
                    description="В разделе опыта работы не найдены даты или периоды работы.",
                    recommendation_text=(
                        "Добавьте периоды работы, например: "
                        "«2021–2024» или «май 2021 — декабрь 2023»."
                    ),
                    evidence_fragment=experience_section.text,
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
from uuid import uuid4

from app.agents.formal.base import BaseFormalAgent
from app.schemas.checks import Issue, Recommendation
from app.schemas.common import Severity
from app.schemas.documents import ParsedDocument


class SectionStructureAgent(BaseFormalAgent):
    """
    Агент проверки структуры документа.

    Проверяет, удалось ли системе распознать смысловые секции:
    contacts, experience, skills, education, projects, summary.
    """

    agent_name = "SectionStructureAgent"

    def check(self, document: ParsedDocument) -> list[Issue]:
        issues: list[Issue] = []

        if not document.sections:
            issues.append(
                self._make_issue(
                    severity=Severity.CRITICAL,
                    issue_type="no_sections",
                    description="В документе не удалось выделить ни одной секции.",
                    recommendation_text="Проверьте формат файла и структуру документа.",
                )
            )
            return issues

        known_sections = [
            section for section in document.sections
            if section.section_type != "unknown"
        ]

        if not known_sections:
            issues.append(
                self._make_issue(
                    severity=Severity.MAJOR,
                    issue_type="unrecognized_structure",
                    description="Система не смогла распознать смысловые разделы документа.",
                    recommendation_text=(
                        "Добавьте явные заголовки разделов: «Контакты», "
                        "«Опыт работы», «Навыки», «Образование»."
                    ),
                )
            )

        short_sections = [
            section for section in document.sections
            if len(section.text.strip()) < 5
        ]

        if short_sections:
            issues.append(
                self._make_issue(
                    severity=Severity.MINOR,
                    issue_type="very_short_sections",
                    description="В документе найдены слишком короткие секции.",
                    recommendation_text="Проверьте, нет ли случайных пустых или неполных строк.",
                    evidence_fragment=short_sections[0].text,
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
            confidence_score=0.8,
        )
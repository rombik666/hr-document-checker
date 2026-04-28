from uuid import uuid4

from app.agents.formal.base import BaseFormalAgent
from app.schemas.checks import Issue, Recommendation
from app.schemas.common import EntityType, Severity
from app.schemas.documents import ParsedDocument


class CompletenessAgent(BaseFormalAgent):
    """
    Агент полноты документа.

    Проверяет:
    - есть ли вообще текст;
    - есть ли контакты;
    - есть ли опыт;
    - есть ли навыки;
    - есть ли образование.
    """

    agent_name = "CompletenessAgent"

    def check(self, document: ParsedDocument) -> list[Issue]:
        issues: list[Issue] = []

        raw_text = document.raw_text.strip()

        if not raw_text:
            issues.append(
                self._make_issue(
                    severity=Severity.CRITICAL,
                    issue_type="empty_document",
                    description="Документ не содержит извлечённого текста.",
                    recommendation_text="Проверьте файл и загрузите документ с читаемым текстом.",
                )
            )
            return issues

        emails = [
            entity for entity in document.entities
            if entity.entity_type == EntityType.EMAIL
        ]
        phones = [
            entity for entity in document.entities
            if entity.entity_type == EntityType.PHONE
        ]
        skills = [
            entity for entity in document.entities
            if entity.entity_type == EntityType.SKILL
        ]

        section_types = {section.section_type for section in document.sections}

        if not emails and not phones:
            issues.append(
                self._make_issue(
                    severity=Severity.CRITICAL,
                    issue_type="missing_contacts",
                    description="В документе отсутствуют контактные данные: не найден e-mail и номер телефона.",
                    recommendation_text="Добавьте в резюме e-mail и номер телефона для связи.",
                )
            )

        if not emails:
            issues.append(
                self._make_issue(
                    severity=Severity.MAJOR,
                    issue_type="missing_email",
                    description="В документе не найден e-mail.",
                    recommendation_text="Добавьте актуальный e-mail в блок контактов.",
                )
            )

        if not phones:
            issues.append(
                self._make_issue(
                    severity=Severity.MAJOR,
                    issue_type="missing_phone",
                    description="В документе не найден номер телефона.",
                    recommendation_text="Добавьте номер телефона в международном или российском формате.",
                )
            )

        if "experience" not in section_types:
            issues.append(
                self._make_issue(
                    severity=Severity.MAJOR,
                    issue_type="missing_experience_section",
                    description="В документе не найден явно выраженный раздел опыта работы.",
                    recommendation_text="Добавьте раздел «Опыт работы» с описанием должностей, компаний и периодов.",
                )
            )

        if "skills" not in section_types and not skills:
            issues.append(
                self._make_issue(
                    severity=Severity.MAJOR,
                    issue_type="missing_skills_section",
                    description="В документе не найден раздел навыков или список технических навыков.",
                    recommendation_text="Добавьте раздел «Навыки» и перечислите ключевые технологии и инструменты.",
                )
            )

        if "education" not in section_types:
            issues.append(
                self._make_issue(
                    severity=Severity.MINOR,
                    issue_type="missing_education_section",
                    description="В документе не найден явно выраженный раздел образования.",
                    recommendation_text="Добавьте раздел «Образование», если он релевантен для вакансии.",
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
            confidence_score=0.9,
        )
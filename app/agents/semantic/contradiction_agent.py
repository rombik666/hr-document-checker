import re
from uuid import uuid4

from app.agents.semantic.base import BaseSemanticAgent
from app.schemas.checks import Issue, Recommendation
from app.schemas.common import Severity
from app.schemas.documents import ParsedDocument
from app.schemas.rag import RagContext


class ContradictionAgent(BaseSemanticAgent):
    """
    Агент поиска потенциальных противоречий.

    """

    agent_name = "ContradictionAgent"

    YEAR_PATTERN = re.compile(r"\b(?:19|20)\d{2}\b")

    def check(
        self,
        document: ParsedDocument,
        rag_context: RagContext | None = None,
        vacancy_text: str | None = None,
    ) -> list[Issue]:
        issues: list[Issue] = []
        text_lower = document.raw_text.lower()

        years = [
            int(match.group(0))
            for match in self.YEAR_PATTERN.finditer(document.raw_text)
        ]

        has_senior = any(
            marker in text_lower
            for marker in ["senior", "ведущий", "старший"]
        )

        if has_senior and len(years) >= 2:
            experience_span = max(years) - min(years)

            if experience_span < 2:
                issues.append(
                    self._make_issue(
                        severity=Severity.MAJOR,
                        issue_type="possible_senior_experience_mismatch",
                        description=(
                            "В документе заявлен senior/старший уровень, "
                            "но найденный временной диапазон опыта выглядит слишком коротким."
                        ),
                        recommendation_text=(
                            "Проверьте, достаточно ли подробно описан опыт для заявленного уровня. "
                            "Добавьте периоды работы, проекты, зону ответственности и достижения."
                        ),
                        evidence_fragment="senior / старший",
                    )
                )

        has_backend_role = any(
            marker in text_lower
            for marker in ["backend", "бэкенд", "бекенд"]
        )

        has_backend_skills = any(
            marker in text_lower
            for marker in ["fastapi", "django", "postgresql", "rest api", "api"]
        )

        if has_backend_role and not has_backend_skills:
            issues.append(
                self._make_issue(
                    severity=Severity.MAJOR,
                    issue_type="backend_role_without_backend_skills",
                    description=(
                        "В документе заявлена backend-роль, но не найдены типичные backend-навыки "
                        "или технологии."
                    ),
                    recommendation_text=(
                        "Добавьте релевантные backend-технологии: FastAPI/Django, PostgreSQL, REST API, Docker."
                    ),
                    evidence_fragment="backend",
                )
            )

        return issues

    def _make_issue(
        self,
        severity: Severity,
        issue_type: str,
        description: str,
        recommendation_text: str,
        evidence_fragment: str | None,
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
            confidence_score=0.7,
        )
import re
from uuid import uuid4

from app.agents.semantic.base import BaseSemanticAgent
from app.schemas.checks import Issue, Recommendation
from app.schemas.common import Severity
from app.schemas.documents import ParsedDocument
from app.schemas.rag import RagContext


class VacancyRelevanceAgent(BaseSemanticAgent):
    """
    Агент релевантности вакансии.

    """

    agent_name = "VacancyRelevanceAgent"

    IMPORTANT_SKILLS = [
        "python",
        "fastapi",
        "django",
        "postgresql",
        "mysql",
        "docker",
        "git",
        "linux",
        "rest api",
        "api",
        "pandas",
        "numpy",
        "pytorch",
        "tensorflow",
        "rag",
        "llm",
        "machine learning",
    ]

    def check(
        self,
        document: ParsedDocument,
        rag_context: RagContext | None = None,
        vacancy_text: str | None = None,
    ) -> list[Issue]:
        if not vacancy_text:
            return []

        document_text = document.raw_text.lower()
        vacancy_text_lower = vacancy_text.lower()

        required_skills = self._extract_required_skills(vacancy_text_lower)

        if not required_skills:
            return []

        covered_skills = [
            skill for skill in required_skills
            if skill in document_text
        ]

        missing_skills = [
            skill for skill in required_skills
            if skill not in document_text
        ]

        coverage_percent = round(len(covered_skills) / len(required_skills) * 100, 2)

        issues: list[Issue] = []

        if coverage_percent < 50:
            severity = Severity.CRITICAL
        elif coverage_percent < 75:
            severity = Severity.MAJOR
        else:
            severity = Severity.MINOR

        if missing_skills:
            issues.append(
                Issue(
                    issue_id=str(uuid4()),
                    severity=severity,
                    issue_type="vacancy_requirements_gap",
                    description=(
                        "Резюме не полностью покрывает требования вакансии. "
                        f"Покрытие найденных требований: {coverage_percent}%."
                    ),
                    evidence_fragment=", ".join(missing_skills),
                    recommendation=Recommendation(
                        recommendation_id=str(uuid4()),
                        recommendation_text=(
                            "Проверьте, действительно ли отсутствующие навыки есть в опыте. "
                            "Если да — добавьте их в раздел навыков или описание проектов. "
                            "Если нет — учитывайте это как пробел относительно вакансии."
                        ),
                        example_fix=(
                            "Например: «FastAPI — разработка REST API», "
                            "«PostgreSQL — проектирование таблиц и SQL-запросов»."
                        ),
                    ),
                    source_agent=self.agent_name,
                    confidence_score=0.8,
                    metadata={
                        "coverage_percent": coverage_percent,
                        "covered_skills": covered_skills,
                        "missing_skills": missing_skills,
                        "required_skills": required_skills,
                    },
                )
            )

        return issues

    def _extract_required_skills(self, vacancy_text: str) -> list[str]:
        required: list[str] = []

        for skill in self.IMPORTANT_SKILLS:
            pattern = self._build_skill_pattern(skill)

            if pattern.search(vacancy_text):
                required.append(skill)

        return required

    @staticmethod
    def _build_skill_pattern(skill: str) -> re.Pattern[str]:
        escaped_skill = re.escape(skill.lower())
        return re.compile(rf"(?<![a-zа-яё0-9]){escaped_skill}(?![a-zа-яё0-9])")
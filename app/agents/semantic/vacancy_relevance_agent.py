import re
from dataclasses import dataclass
from uuid import uuid4

from app.agents.semantic.base import BaseSemanticAgent
from app.schemas.checks import Issue, Recommendation
from app.schemas.common import Severity
from app.schemas.documents import ParsedDocument
from app.schemas.rag import RagContext


@dataclass(frozen=True)
class VacancyCoverageAnalysis:
    required_skills: list[str]
    covered_skills: list[str]
    missing_skills: list[str]
    coverage_percent: float


class VacancyRelevanceAgent(BaseSemanticAgent):
    """
    Агент релевантности вакансии.

    """

    agent_name = "VacancyRelevanceAgent"

    SKILL_ALIASES: dict[str, list[str]] = {
        "python": ["python", "питон"],
        "fastapi": ["fastapi", "fast api"],
        "django": ["django"],
        "postgresql": ["postgresql", "postgre sql", "postgres", "postgres sql"],
        "mysql": ["mysql", "my sql"],
        "sqlalchemy": ["sqlalchemy", "sql alchemy"],
        "alembic": ["alembic"],
        "docker": ["docker"],
        "docker compose": [
            "docker compose",
            "docker-compose",
            "docker-compose.yml",
            "docker compose.yml",
        ],
        "git": ["git"],
        "linux": ["linux"],
        "rest api": ["rest api", "restful api", "rest"],
        "redis": ["redis"],
        "nginx": ["nginx"],
        "prometheus": ["prometheus"],
        "grafana": ["grafana"],
        "pandas": ["pandas"],
        "numpy": ["numpy"],
        "pytorch": ["pytorch", "py torch"],
        "tensorflow": ["tensorflow", "tensor flow"],
        "rag": ["rag", "retrieval augmented generation"],
        "llm": ["llm", "large language model", "языковая модель"],
        "machine learning": ["machine learning", "ml", "машинное обучение"],
        "pytest": ["pytest", "py test"],
    }

    SKILL_LABELS: dict[str, str] = {
        "python": "Python",
        "fastapi": "FastAPI",
        "django": "Django",
        "postgresql": "PostgreSQL",
        "mysql": "MySQL",
        "sqlalchemy": "SQLAlchemy",
        "alembic": "Alembic",
        "docker": "Docker",
        "docker compose": "Docker Compose",
        "git": "Git",
        "linux": "Linux",
        "rest api": "REST API",
        "redis": "Redis",
        "nginx": "Nginx",
        "prometheus": "Prometheus",
        "grafana": "Grafana",
        "pandas": "Pandas",
        "numpy": "NumPy",
        "pytorch": "PyTorch",
        "tensorflow": "TensorFlow",
        "rag": "RAG",
        "llm": "LLM",
        "machine learning": "Machine Learning",
        "pytest": "pytest",
    }

    IMPORTANT_SKILLS = list(SKILL_ALIASES.keys())

    def check(
        self,
        document: ParsedDocument,
        rag_context: RagContext | None = None,
        vacancy_text: str | None = None,
    ) -> list[Issue]:
        if not vacancy_text:
            return []

        analysis = self.analyze_texts(
            document_text=document.raw_text,
            vacancy_text=vacancy_text,
        )

        if not analysis.required_skills:
            return []

        if not analysis.missing_skills:
            return []

        if analysis.coverage_percent < 50:
            severity = Severity.CRITICAL
        elif analysis.coverage_percent < 75:
            severity = Severity.MAJOR
        else:
            severity = Severity.MINOR

        covered_labels = self.label_skills(analysis.covered_skills)
        missing_labels = self.label_skills(analysis.missing_skills)
        required_labels = self.label_skills(analysis.required_skills)

        return [
            Issue(
                issue_id=str(uuid4()),
                severity=severity,
                issue_type="vacancy_requirements_gap",
                description=(
                    "Резюме не полностью покрывает требования вакансии. "
                    f"Покрытие найденных требований: {analysis.coverage_percent}%."
                ),
                evidence_fragment=", ".join(missing_labels),
                recommendation=Recommendation(
                    recommendation_id=str(uuid4()),
                    recommendation_text=(
                        "Проверьте, действительно ли отсутствующие навыки есть в опыте, "
                        "проектах или разделе навыков. Если да — добавьте более явное "
                        "описание применения этих технологий. Если нет — учитывайте это "
                        "как пробел относительно вакансии."
                    ),
                    example_fix=(
                        "Например: «PostgreSQL — проектирование схем, индексов и SQL-запросов», "
                        "«Docker Compose — настройка локального и серверного окружения»."
                    ),
                ),
                source_agent=self.agent_name,
                confidence_score=0.8,
                metadata={
                    "coverage_percent": analysis.coverage_percent,

                    # Канонические значения — для обратной совместимости и тестов.
                    "covered_skills": analysis.covered_skills,
                    "missing_skills": analysis.missing_skills,
                    "required_skills": analysis.required_skills,

                    # Человекочитаемые значения — для отчёта и UI.
                    "covered_skill_labels": covered_labels,
                    "missing_skill_labels": missing_labels,
                    "required_skill_labels": required_labels,
                },
            )
        ]

    @classmethod
    def analyze_texts(
        cls,
        document_text: str,
        vacancy_text: str,
    ) -> VacancyCoverageAnalysis:
        normalized_document = cls._normalize_text(document_text)
        normalized_vacancy = cls._normalize_text(vacancy_text)

        required_skills = cls._extract_required_skills(normalized_vacancy)

        if not required_skills:
            return VacancyCoverageAnalysis(
                required_skills=[],
                covered_skills=[],
                missing_skills=[],
                coverage_percent=100.0,
            )

        covered_skills = [
            skill for skill in required_skills
            if cls._skill_is_present(skill, normalized_document)
        ]

        missing_skills = [
            skill for skill in required_skills
            if skill not in covered_skills
        ]

        coverage_percent = round(
            len(covered_skills) / len(required_skills) * 100,
            2,
        )

        return VacancyCoverageAnalysis(
            required_skills=required_skills,
            covered_skills=covered_skills,
            missing_skills=missing_skills,
            coverage_percent=coverage_percent,
        )

    @classmethod
    def label_skills(cls, skills: list[str]) -> list[str]:
        return [
            cls.SKILL_LABELS.get(skill, skill)
            for skill in skills
        ]

    @classmethod
    def _extract_required_skills(cls, normalized_vacancy_text: str) -> list[str]:
        required: list[str] = []

        for skill in cls.IMPORTANT_SKILLS:
            if cls._skill_is_present(skill, normalized_vacancy_text):
                required.append(skill)

        return required

    @classmethod
    def _skill_is_present(cls, skill: str, normalized_text: str) -> bool:
        aliases = cls.SKILL_ALIASES.get(skill, [skill])

        return any(
            cls._build_alias_pattern(alias).search(normalized_text)
            for alias in aliases
        )

    @staticmethod
    def _normalize_text(text: str) -> str:
        normalized = text.lower()
        normalized = normalized.replace("ё", "е")
        normalized = normalized.replace("-", " ")
        normalized = normalized.replace("_", " ")
        normalized = normalized.replace("/", " ")
        normalized = normalized.replace("\\", " ")

        return re.sub(r"\s+", " ", normalized).strip()

    @classmethod
    def _build_alias_pattern(cls, alias: str) -> re.Pattern[str]:
        normalized_alias = cls._normalize_text(alias)
        escaped_parts = [
            re.escape(part)
            for part in normalized_alias.split()
            if part
        ]

        if not escaped_parts:
            return re.compile(r"$^")

        alias_pattern = r"\s+".join(escaped_parts)

        return re.compile(
            rf"(?<![a-zа-яе0-9]){alias_pattern}(?![a-zа-яе0-9])"
        )
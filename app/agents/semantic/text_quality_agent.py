from uuid import uuid4

from app.agents.semantic.base import BaseSemanticAgent
from app.schemas.checks import Issue, Recommendation
from app.schemas.common import Severity
from app.schemas.documents import ParsedDocument
from app.schemas.rag import RagContext


class TextQualityAgent(BaseSemanticAgent):
    """
    Агент качества текста.

    Проверяет:
    - слишком общие формулировки;
    - отсутствие конкретики;
    - признаки «воды».
    """

    agent_name = "TextQualityAgent"

    WEAK_PHRASES = [
        "занимался разработкой",
        "участвовал в разработке",
        "работал с",
        "имею опыт",
        "принимал участие",
        "выполнял задачи",
        "ответственный",
        "коммуникабельный",
        "стрессоустойчивый",
        "быстро обучаюсь",
    ]

    WATER_PHRASES = [
        "нацелен на результат",
        "умею работать в команде",
        "хорошие коммуникативные навыки",
        "активная жизненная позиция",
        "желание развиваться",
    ]

    def check(
        self,
        document: ParsedDocument,
        rag_context: RagContext | None = None,
        vacancy_text: str | None = None,
    ) -> list[Issue]:
        issues: list[Issue] = []
        text_lower = document.raw_text.lower()

        for phrase in self.WEAK_PHRASES:
            if phrase in text_lower:
                issues.append(
                    self._make_issue(
                        severity=Severity.MAJOR,
                        issue_type="weak_phrase",
                        description=(
                            f"В документе найдена слабая или слишком общая формулировка: "
                            f"«{phrase}»."
                        ),
                        recommendation_text=(
                            "Замените общую формулировку на конкретное описание результата: "
                            "что именно было сделано, с помощью каких технологий и какой эффект получен."
                        ),
                        evidence_fragment=phrase,
                        rag_context=rag_context,
                    )
                )

        for phrase in self.WATER_PHRASES:
            if phrase in text_lower:
                issues.append(
                    self._make_issue(
                        severity=Severity.MINOR,
                        issue_type="water_phrase",
                        description=(
                            f"В документе найдена шаблонная фраза, которая может восприниматься как «вода»: "
                            f"«{phrase}»."
                        ),
                        recommendation_text=(
                            "Замените шаблонную характеристику на конкретный пример из опыта."
                        ),
                        evidence_fragment=phrase,
                        rag_context=rag_context,
                    )
                )

        return self._deduplicate(issues)

    def _make_issue(
        self,
        severity: Severity,
        issue_type: str,
        description: str,
        recommendation_text: str,
        evidence_fragment: str | None,
        rag_context: RagContext | None,
    ) -> Issue:
        metadata = {}

        if rag_context and rag_context.results:
            metadata["rag_sources"] = [
                {
                    "title": result.title,
                    "score": result.score,
                }
                for result in rag_context.results[:3]
            ]

        return Issue(
            issue_id=str(uuid4()),
            severity=severity,
            issue_type=issue_type,
            description=description,
            evidence_fragment=evidence_fragment,
            recommendation=Recommendation(
                recommendation_id=str(uuid4()),
                recommendation_text=recommendation_text,
                example_fix=(
                    "Например: «Разработал REST API на FastAPI для обработки заявок "
                    "и настроил хранение данных в PostgreSQL»."
                ),
            ),
            source_agent=self.agent_name,
            confidence_score=0.75,
            metadata=metadata,
        )

    @staticmethod
    def _deduplicate(issues: list[Issue]) -> list[Issue]:
        unique: dict[tuple[str, str | None], Issue] = {}

        for issue in issues:
            key = (issue.issue_type, issue.evidence_fragment)
            unique[key] = issue

        return list(unique.values())
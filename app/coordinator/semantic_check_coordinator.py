from app.agents.semantic.contradiction_agent import ContradictionAgent
from app.agents.semantic.text_quality_agent import TextQualityAgent
from app.agents.semantic.vacancy_relevance_agent import VacancyRelevanceAgent
from app.rag.service import RagService
from app.schemas.checks import CheckResult, Issue, SemanticCheckResponse
from app.schemas.common import Severity
from app.schemas.documents import ParsedDocument
from app.schemas.rag import RagSearchRequest


class SemanticCheckCoordinator:
    """
    Координатор семантических проверок.

    """

    def __init__(self) -> None:
        self.rag_service = RagService()
        self.agents = [
            TextQualityAgent(),
            ContradictionAgent(),
            VacancyRelevanceAgent(),
        ]

    def run(
        self,
        document: ParsedDocument,
        vacancy_text: str | None = None,
    ) -> SemanticCheckResponse:
        rag_query = self._build_rag_query(
            document=document,
            vacancy_text=vacancy_text,
        )

        rag_context = self.rag_service.search(
            RagSearchRequest(
                query=rag_query,
                top_k=3,
            )
        )

        check_results: list[CheckResult] = []

        for agent in self.agents:
            result = agent.run(
                document=document,
                rag_context=rag_context,
                vacancy_text=vacancy_text,
            )
            check_results.append(result)

        issues = self._collect_issues(check_results)

        return SemanticCheckResponse(
            document_id=document.metadata.document_id,
            filename=document.metadata.filename,
            total_issues=len(issues),
            critical_count=self._count_by_severity(issues, Severity.CRITICAL),
            major_count=self._count_by_severity(issues, Severity.MAJOR),
            minor_count=self._count_by_severity(issues, Severity.MINOR),
            check_results=check_results,
        )

    @staticmethod
    def _build_rag_query(
        document: ParsedDocument,
        vacancy_text: str | None = None,
    ) -> str:
        parts = [
            "качество резюме",
            "сильные формулировки",
            document.metadata.document_type.value,
        ]

        if vacancy_text:
            parts.append(vacancy_text[:500])

        return " ".join(parts)

    @staticmethod
    def _collect_issues(check_results: list[CheckResult]) -> list[Issue]:
        issues: list[Issue] = []

        for result in check_results:
            issues.extend(result.issues)

        return issues

    @staticmethod
    def _count_by_severity(issues: list[Issue], severity: Severity) -> int:
        return sum(1 for issue in issues if issue.severity == severity)
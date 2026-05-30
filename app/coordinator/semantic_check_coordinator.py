from sqlalchemy.orm import Session

from app.agents.semantic.contradiction_agent import ContradictionAgent
from app.agents.semantic.llm_semantic_agent import LlmSemanticAgent
from app.agents.semantic.text_quality_agent import TextQualityAgent
from app.agents.semantic.vacancy_relevance_agent import VacancyRelevanceAgent
from app.core.config import settings
from app.rag.service import RagService
from app.schemas.checks import CheckResult, Issue, SemanticCheckResponse
from app.schemas.common import Severity
from app.schemas.documents import ParsedDocument
from app.schemas.rag import RagContext, RagSearchRequest


class SemanticCheckCoordinator:
    """
    Координатор семантических проверок.

    RAG-контекст строится только на основе DB-backed источников,
    загруженных HR/admin-пользователем в rag_sources.

    Candidate не получает корпоративный RAG-контекст.
    Если у HR/admin нет активных источников, проверка выполняется
    с пустым RagContext.
    """

    def __init__(
        self,
        rag_service=None,
        enable_llm_agent: bool | None = None,
    ) -> None:
        self.rag_service = rag_service or RagService()

        self.enable_llm_agent = (
            settings.llm_semantic_agent_enabled
            if enable_llm_agent is None
            else enable_llm_agent
        )

        self.agents = [
            TextQualityAgent(),
            ContradictionAgent(),
            VacancyRelevanceAgent(),
        ]

        if self.enable_llm_agent:
            self.agents.append(LlmSemanticAgent())

    def run(
        self,
        document: ParsedDocument,
        vacancy_text: str | None = None,
        db: Session | None = None,
        user_id: str | None = None,
        user_role: str | None = None,
    ) -> SemanticCheckResponse:
        rag_context = self._build_rag_context(
            document=document,
            vacancy_text=vacancy_text,
            db=db,
            user_id=user_id,
            user_role=user_role,
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

    def _build_rag_context(
        self,
        document: ParsedDocument,
        vacancy_text: str | None = None,
        db: Session | None = None,
        user_id: str | None = None,
        user_role: str | None = None,
    ) -> RagContext:
        rag_query = self._build_rag_query(
            document=document,
            vacancy_text=vacancy_text,
        )

        if (
            db is None
            or user_id is None
            or user_role not in {"hr", "admin"}
        ):
            return RagContext(
                query=rag_query,
                results=[],
            )

        return self.rag_service.search_user_sources(
            request=RagSearchRequest(
                query=rag_query,
                top_k=3,
            ),
            db=db,
            user_id=user_id,
            user_role=user_role,
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
        return sum(
            1
            for issue in issues
            if issue.severity == severity
        )
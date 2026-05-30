from time import perf_counter

from sqlalchemy.orm import Session

from app.agents.semantic.contradiction_agent import ContradictionAgent
from app.agents.semantic.llm_semantic_agent import LlmSemanticAgent
from app.agents.semantic.text_quality_agent import TextQualityAgent
from app.agents.semantic.vacancy_relevance_agent import VacancyRelevanceAgent
from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.checks import CheckResult, Issue, SemanticCheckResponse
from app.schemas.common import Severity
from app.schemas.documents import ParsedDocument
from app.schemas.rag import RagContext, RagSearchRequest
from app.services.rag_index_service import RagIndexNotReadyError, RagIndexService


logger = get_logger(__name__)


class SemanticCheckCoordinator:
    """
    Координатор семантических проверок.

    Для HR/admin RAG-контекст строится через персональный FAISS-индекс.
    Если индекс отсутствует или устарел, проверка не падает: отчёт
    формируется без RAG-контекста, а техническая информация получает
    rag_reindex_required=true.
    """

    def __init__(
        self,
        rag_index_service_cls=RagIndexService,
        enable_llm_agent: bool | None = None,
    ) -> None:
        self.rag_index_service_cls = rag_index_service_cls

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
        rag_started_at = perf_counter()

        rag_context, rag_metadata = self._build_rag_context(
            document=document,
            vacancy_text=vacancy_text,
            db=db,
            user_id=user_id,
            user_role=user_role,
        )

        rag_metadata["rag_build_duration_ms"] = round(
            (perf_counter() - rag_started_at) * 1000,
            3,
        )

        logger.info(
            "semantic_rag_context_built document_id=%s user_role=%s backend=%s used=%s results=%s reindex_required=%s duration_ms=%.3f",
            document.metadata.document_id,
            user_role,
            rag_metadata.get("rag_backend"),
            rag_metadata.get("rag_context_used"),
            len(rag_context.results),
            rag_metadata.get("rag_reindex_required"),
            rag_metadata["rag_build_duration_ms"],
        )

        check_results: list[CheckResult] = []

        for agent in self.agents:
            agent_started_at = perf_counter()

            result = agent.run(
                document=document,
                rag_context=rag_context,
                vacancy_text=vacancy_text,
            )

            logger.info(
                "semantic_agent_completed document_id=%s agent=%s issues=%s duration_ms=%.3f",
                document.metadata.document_id,
                agent.__class__.__name__,
                len(result.issues),
                (perf_counter() - agent_started_at) * 1000,
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
            rag_metadata=rag_metadata,
        )

    def _build_rag_context(
        self,
        document: ParsedDocument,
        vacancy_text: str | None = None,
        db: Session | None = None,
        user_id: str | None = None,
        user_role: str | None = None,
    ) -> tuple[RagContext, dict]:
        rag_query = self._build_rag_query(
            document=document,
            vacancy_text=vacancy_text,
        )

        if (
            db is None
            or user_id is None
            or user_role not in {"hr", "admin"}
        ):
            return (
                RagContext(
                    query=rag_query,
                    results=[],
                ),
                {
                    "rag_backend": "per_user_faiss",
                    "rag_context_used": False,
                    "rag_reindex_required": False,
                    "rag_index_status": "not_applicable",
                    "rag_results_count": 0,
                    "rag_user_scope": "none",
                    "rag_error": None,
                },
            )

        rag_index_service = self.rag_index_service_cls(db)

        try:
            rag_context = rag_index_service.search_user_index(
                owner_user_id=user_id,
                request=RagSearchRequest(
                    query=rag_query,
                    top_k=2,
                ),
            )

            return (
                rag_context,
                {
                    "rag_backend": "per_user_faiss",
                    "rag_context_used": len(rag_context.results) > 0,
                    "rag_reindex_required": False,
                    "rag_index_status": "ready",
                    "rag_results_count": len(rag_context.results),
                    "rag_user_scope": "own",
                    "rag_error": None,
                },
            )

        except RagIndexNotReadyError as error:
            detail = error.to_detail()

            logger.info(
                "semantic_rag_index_not_ready document_id=%s user_id=%s status=%s reindex_required=%s",
                document.metadata.document_id,
                user_id,
                detail.get("index_status"),
                detail.get("reindex_required"),
            )

            return (
                RagContext(
                    query=rag_query,
                    results=[],
                ),
                {
                    "rag_backend": "per_user_faiss",
                    "rag_context_used": False,
                    "rag_reindex_required": True,
                    "rag_index_status": detail.get("index_status"),
                    "rag_results_count": 0,
                    "rag_user_scope": "own",
                    "rag_error": detail.get("message"),
                    "rag_reindex_endpoint": detail.get("reindex_endpoint"),
                },
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
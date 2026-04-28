from abc import ABC, abstractmethod
from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4

from app.schemas.checks import AgentExecutionInfo, CheckResult, Issue
from app.schemas.common import CheckStatus, CheckType
from app.schemas.documents import ParsedDocument
from app.schemas.rag import RagContext


class BaseSemanticAgent(ABC):
    """
    Базовый класс для семантических агентов.

    """

    agent_name: str = "BaseSemanticAgent"
    ruleset_version: str = "semantic-ruleset-1.0.0"

    def run(
        self,
        document: ParsedDocument,
        rag_context: RagContext | None = None,
        vacancy_text: str | None = None,
    ) -> CheckResult:
        started_at = datetime.now(timezone.utc)
        start_time = perf_counter()

        try:
            issues = self.check(
                document=document,
                rag_context=rag_context,
                vacancy_text=vacancy_text,
            )
            status = CheckStatus.SUCCESS
            error_message = None

        except Exception as error:
            issues = []
            status = CheckStatus.FAILED
            error_message = str(error)

        ended_at = datetime.now(timezone.utc)
        duration_ms = round((perf_counter() - start_time) * 1000, 3)

        execution = AgentExecutionInfo(
            check_id=str(uuid4()),
            agent_name=self.agent_name,
            check_type=CheckType.SEMANTIC,
            status=status,
            started_at=started_at,
            ended_at=ended_at,
            duration_ms=duration_ms,
            model_or_ruleset_version=self.ruleset_version,
            error_message=error_message,
        )

        return CheckResult(
            execution=execution,
            issues=issues,
        )

    @abstractmethod
    def check(
        self,
        document: ParsedDocument,
        rag_context: RagContext | None = None,
        vacancy_text: str | None = None,
    ) -> list[Issue]:
        raise NotImplementedError
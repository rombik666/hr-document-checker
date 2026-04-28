from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import CheckStatus, CheckType, Severity


class Recommendation(BaseModel):
    recommendation_id: str
    recommendation_text: str
    example_fix: str | None = None
    priority_order: int = 0


class Issue(BaseModel):
    issue_id: str
    severity: Severity
    issue_type: str
    description: str
    evidence_fragment: str | None = None
    recommendation: Recommendation | None = None
    source_agent: str
    confidence_score: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentExecutionInfo(BaseModel):
    """
    Техническая информация о запуске агента.
    """

    check_id: str
    agent_name: str
    check_type: CheckType
    status: CheckStatus
    started_at: datetime
    ended_at: datetime
    duration_ms: float
    model_or_ruleset_version: str = "ruleset-1.0.0"
    error_message: str | None = None


class CheckResult(BaseModel):
    """
    Результат работы одного агента проверки.
    """

    execution: AgentExecutionInfo
    issues: list[Issue] = Field(default_factory=list)


class FormalCheckResponse(BaseModel):
    """
    Ответ API для формальных проверок.
    """

    document_id: str
    filename: str
    total_issues: int
    critical_count: int
    major_count: int
    minor_count: int
    check_results: list[CheckResult]
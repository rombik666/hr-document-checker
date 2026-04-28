from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.checks import CheckResult, Issue
from app.schemas.common import ReportStatus


class VacancyRelevance(BaseModel):

    coverage_percent: float | None = None
    covered_requirements: list[str] = Field(default_factory=list)
    missing_requirements: list[str] = Field(default_factory=list)
    comment: str | None = None


class TechnicalInfo(BaseModel):

    generated_at: datetime
    checks_completed: list[str] = Field(default_factory=list)
    failed_checks: list[str] = Field(default_factory=list)
    ruleset_versions: list[str] = Field(default_factory=list)
    total_agents_count: int = 0
    successful_agents_count: int = 0
    failed_agents_count: int = 0
    parser_warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Report(BaseModel):

    report_id: str
    document_id: str
    filename: str

    summary_status: ReportStatus
    summary: str

    total_issues: int
    critical_count: int
    major_count: int
    minor_count: int

    critical: list[Issue] = Field(default_factory=list)
    major: list[Issue] = Field(default_factory=list)
    minor: list[Issue] = Field(default_factory=list)

    vacancy_relevance: VacancyRelevance | None = None
    technical_info: TechnicalInfo

    raw_check_results: list[CheckResult] = Field(default_factory=list)
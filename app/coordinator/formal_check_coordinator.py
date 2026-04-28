from app.agents.formal.completeness_agent import CompletenessAgent
from app.agents.formal.contact_validation_agent import ContactValidationAgent
from app.agents.formal.date_presence_agent import DatePresenceAgent
from app.agents.formal.section_structure_agent import SectionStructureAgent
from app.schemas.checks import CheckResult, FormalCheckResponse, Issue
from app.schemas.common import Severity
from app.schemas.documents import ParsedDocument


class FormalCheckCoordinator:
    """
    Координатор формальных проверок.

    """

    def __init__(self) -> None:
        self.agents = [
            CompletenessAgent(),
            ContactValidationAgent(),
            SectionStructureAgent(),
            DatePresenceAgent(),
        ]

    def run(self, document: ParsedDocument) -> FormalCheckResponse:
        check_results: list[CheckResult] = []

        for agent in self.agents:
            result = agent.run(document)
            check_results.append(result)

        issues = self._collect_issues(check_results)

        return FormalCheckResponse(
            document_id=document.metadata.document_id,
            filename=document.metadata.filename,
            total_issues=len(issues),
            critical_count=self._count_by_severity(issues, Severity.CRITICAL),
            major_count=self._count_by_severity(issues, Severity.MAJOR),
            minor_count=self._count_by_severity(issues, Severity.MINOR),
            check_results=check_results,
        )

    @staticmethod
    def _collect_issues(check_results: list[CheckResult]) -> list[Issue]:
        issues: list[Issue] = []

        for result in check_results:
            issues.extend(result.issues)

        return issues

    @staticmethod
    def _count_by_severity(issues: list[Issue], severity: Severity) -> int:
        return sum(1 for issue in issues if issue.severity == severity)
from datetime import datetime, timezone
from uuid import uuid4

from app.schemas.checks import CheckResult, FormalCheckResponse, Issue
from app.schemas.common import CheckStatus, ReportStatus, Severity
from app.schemas.documents import ParsedDocument
from app.schemas.reports import Report, TechnicalInfo


class ReportBuilder:
    """
    Генератор итогового отчёта.

    Он получает:
    - ParsedDocument;
    - FormalCheckResponse;

    И превращает технические результаты агентов в удобный итоговый Report.
    """

    def build(
        self,
        document: ParsedDocument,
        formal_check_response: FormalCheckResponse,
    ) -> Report:
        check_results = formal_check_response.check_results
        issues = self._collect_issues(check_results)

        critical = self._filter_by_severity(issues, Severity.CRITICAL)
        major = self._filter_by_severity(issues, Severity.MAJOR)
        minor = self._filter_by_severity(issues, Severity.MINOR)

        summary_status = self._get_summary_status(
            critical_count=len(critical),
            major_count=len(major),
        )

        summary = self._build_summary(
            critical_count=len(critical),
            major_count=len(major),
            minor_count=len(minor),
        )

        technical_info = self._build_technical_info(
            document=document,
            check_results=check_results,
        )

        return Report(
            report_id=str(uuid4()),
            document_id=document.metadata.document_id,
            filename=document.metadata.filename,
            summary_status=summary_status,
            summary=summary,
            total_issues=len(issues),
            critical_count=len(critical),
            major_count=len(major),
            minor_count=len(minor),
            critical=critical,
            major=major,
            minor=minor,
            vacancy_relevance=None,
            technical_info=technical_info,
            raw_check_results=check_results,
        )

    @staticmethod
    def _collect_issues(check_results: list[CheckResult]) -> list[Issue]:
        issues: list[Issue] = []

        for result in check_results:
            issues.extend(result.issues)

        return issues

    @staticmethod
    def _filter_by_severity(issues: list[Issue], severity: Severity) -> list[Issue]:
        return [
            issue for issue in issues
            if issue.severity == severity
        ]

    @staticmethod
    def _get_summary_status(
        critical_count: int,
        major_count: int,
    ) -> ReportStatus:
        if critical_count > 0 or major_count > 0:
            return ReportStatus.REQUIRES_REVISION

        return ReportStatus.READY

    @staticmethod
    def _build_summary(
        critical_count: int,
        major_count: int,
        minor_count: int,
    ) -> str:
        if critical_count > 0:
            return (
                "Документ требует серьёзной доработки: "
                f"найдено критических проблем: {critical_count}, "
                f"значимых замечаний: {major_count}, "
                f"незначительных замечаний: {minor_count}."
            )

        if major_count > 0:
            return (
                "Документ требует доработки: "
                f"найдено значимых замечаний: {major_count}, "
                f"незначительных замечаний: {minor_count}."
            )

        if minor_count > 0:
            return (
                "Документ в целом готов, но есть небольшие замечания: "
                f"{minor_count}."
            )

        return "Документ успешно прошёл формальные проверки. Значимых проблем не найдено."

    @staticmethod
    def _build_technical_info(
        document: ParsedDocument,
        check_results: list[CheckResult],
    ) -> TechnicalInfo:
        completed: list[str] = []
        failed: list[str] = []
        versions: set[str] = set()

        for result in check_results:
            execution = result.execution

            versions.add(execution.model_or_ruleset_version)

            if execution.status == CheckStatus.SUCCESS:
                completed.append(execution.agent_name)

            if execution.status == CheckStatus.FAILED:
                failed.append(execution.agent_name)

        return TechnicalInfo(
            generated_at=datetime.now(timezone.utc),
            checks_completed=completed,
            failed_checks=failed,
            ruleset_versions=sorted(versions),
            total_agents_count=len(check_results),
            successful_agents_count=len(completed),
            failed_agents_count=len(failed),
            parser_warnings=document.metadata.warnings,
            metadata={
                "source_format": document.metadata.source_format.value,
                "document_type": document.metadata.document_type.value,
                "storage_mode": document.metadata.storage_mode.value,
                "sections_count": len(document.sections),
                "entities_count": len(document.entities),
            },
        )
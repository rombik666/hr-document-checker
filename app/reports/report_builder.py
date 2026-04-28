from datetime import datetime, timezone
from uuid import uuid4

from app.schemas.checks import CheckResult, FormalCheckResponse, Issue, SemanticCheckResponse
from app.schemas.common import CheckStatus, ReportStatus, Severity
from app.schemas.documents import ParsedDocument
from app.schemas.reports import Report, TechnicalInfo, VacancyRelevance


class ReportBuilder:
    """
    Генератор итогового отчёта.

    """

    def build(
        self,
        document: ParsedDocument,
        formal_check_response: FormalCheckResponse,
        semantic_check_response: SemanticCheckResponse | None = None,
        vacancy_text: str | None = None,
    ) -> Report:
        check_results = list(formal_check_response.check_results)

        if semantic_check_response:
            check_results.extend(semantic_check_response.check_results)

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
            semantic_checks_enabled=semantic_check_response is not None,
        )

        technical_info = self._build_technical_info(
            document=document,
            check_results=check_results,
            semantic_checks_enabled=semantic_check_response is not None,
            vacancy_text_provided=vacancy_text is not None,
        )

        vacancy_relevance = self._build_vacancy_relevance(
            issues=issues,
            vacancy_text=vacancy_text,
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
            vacancy_relevance=vacancy_relevance,
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
        semantic_checks_enabled: bool,
    ) -> str:
        check_type_text = (
            "формальные и семантические проверки"
            if semantic_checks_enabled
            else "формальные проверки"
        )

        if critical_count > 0:
            return (
                f"Документ требует серьёзной доработки: {check_type_text} выявили "
                f"критических проблем: {critical_count}, "
                f"значимых замечаний: {major_count}, "
                f"незначительных замечаний: {minor_count}."
            )

        if major_count > 0:
            return (
                f"Документ требует доработки: {check_type_text} выявили "
                f"значимых замечаний: {major_count}, "
                f"незначительных замечаний: {minor_count}."
            )

        if minor_count > 0:
            return (
                f"Документ в целом готов, но {check_type_text} выявили "
                f"небольшие замечания: {minor_count}."
            )

        return (
            f"Документ успешно прошёл {check_type_text}. "
            "Значимых проблем не найдено."
        )

    @staticmethod
    def _build_technical_info(
        document: ParsedDocument,
        check_results: list[CheckResult],
        semantic_checks_enabled: bool,
        vacancy_text_provided: bool,
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
                "semantic_checks_enabled": semantic_checks_enabled,
                "vacancy_text_provided": vacancy_text_provided,
            },
        )

    @staticmethod
    def _build_vacancy_relevance(
        issues: list[Issue],
        vacancy_text: str | None,
    ) -> VacancyRelevance | None:
        """
        Формирует блок релевантности вакансии.

        Если vacancy_text не передан, блок не нужен.
        Если vacancy_text передан и агент релевантности нашёл пробелы,
        данные берутся из metadata соответствующей проблемы.
        """

        if not vacancy_text:
            return None

        relevance_issues = [
            issue for issue in issues
            if issue.issue_type == "vacancy_requirements_gap"
        ]

        if not relevance_issues:
            return VacancyRelevance(
                coverage_percent=100.0,
                covered_requirements=[],
                missing_requirements=[],
                comment=(
                    "По найденным ключевым требованиям явных пробелов относительно вакансии не обнаружено."
                ),
            )

        issue = relevance_issues[0]
        metadata = issue.metadata

        return VacancyRelevance(
            coverage_percent=metadata.get("coverage_percent"),
            covered_requirements=metadata.get("covered_skills", []),
            missing_requirements=metadata.get("missing_skills", []),
            comment=issue.description,
        )
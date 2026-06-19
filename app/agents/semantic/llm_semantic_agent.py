from datetime import datetime, timezone
from uuid import uuid4

from app.core.logging import get_logger
from app.llm.factory import create_llm_client
from app.llm.json_parser import extract_json_from_text
from app.schemas.checks import AgentExecutionInfo, CheckResult, Issue, Recommendation
from app.schemas.common import CheckStatus, CheckType, Severity
from app.schemas.documents import ParsedDocument
from app.schemas.rag import RagContext

from app.agents.semantic.vacancy_relevance_agent import VacancyRelevanceAgent


logger = get_logger(__name__)


class LlmSemanticAgent:

    agent_name = "LlmSemanticAgent"
    check_type = CheckType.SEMANTIC
    model_or_ruleset_version = "llm-agent-1.0.1"

    def run(
        self,
        document: ParsedDocument,
        rag_context: RagContext,
        vacancy_text: str | None = None,
    ) -> CheckResult:
        started_at = datetime.now(timezone.utc)

        try:
            issues = self._run_llm_analysis(
                document=document,
                rag_context=rag_context,
                vacancy_text=vacancy_text,
            )

            ended_at = datetime.now(timezone.utc)

            return CheckResult(
                execution=AgentExecutionInfo(
                    check_id=str(uuid4()),
                    agent_name=self.agent_name,
                    check_type=self.check_type,
                    status=CheckStatus.SUCCESS,
                    started_at=started_at,
                    ended_at=ended_at,
                    duration_ms=self._duration_ms(started_at, ended_at),
                    model_or_ruleset_version=self.model_or_ruleset_version,
                    error_message=None,
                ),
                issues=issues,
            )

        except Exception as error:
            ended_at = datetime.now(timezone.utc)

            logger.exception(
                "llm_semantic_agent_failed document_id=%s",
                document.metadata.document_id,
            )

            return CheckResult(
                execution=AgentExecutionInfo(
                    check_id=str(uuid4()),
                    agent_name=self.agent_name,
                    check_type=self.check_type,
                    status=CheckStatus.FAILED,
                    started_at=started_at,
                    ended_at=ended_at,
                    duration_ms=self._duration_ms(started_at, ended_at),
                    model_or_ruleset_version=self.model_or_ruleset_version,
                    error_message=str(error),
                ),
                issues=[],
            )

    def _run_llm_analysis(
        self,
        document: ParsedDocument,
        rag_context: RagContext,
        vacancy_text: str | None,
    ) -> list[Issue]:
        client = create_llm_client()

        prompt = self._build_prompt(
            document=document,
            rag_context=rag_context,
            vacancy_text=vacancy_text,
        )

        response = client.generate(
            system_prompt=self._system_prompt(),
            prompt=prompt,
            temperature=0.25,
            max_tokens=350,
        )

        parsed = extract_json_from_text(response.text)

        return self._parse_issues(
            parsed=parsed,
            document_text=document.raw_text,
        )

    @staticmethod
    def _system_prompt() -> str:
        return (
            "Ты — агент проверки качества HR-документов. "
            "Ты анализируешь резюме, сопроводительные письма и анкеты кандидатов. "
            "Отвечай только на русском языке. "
            "Не выдумывай факты. "
            "Каждое замечание должно опираться только на предоставленный текст документа. "
            "Если доказательства нет, не создавай замечание. "
            "Отсутствие текста вакансии само по себе не является ошибкой документа. "
            "Верни только валидный JSON без Markdown и пояснений."
        )

    @staticmethod
    def _build_prompt(
        document: ParsedDocument,
        rag_context: RagContext,
        vacancy_text: str | None,
    ) -> str:
        document_text = document.raw_text[:3000]

        rag_fragments = "\n\n".join(
            f"[{index + 1}] {result.text[:700]}"
            for index, result in enumerate(rag_context.results[:2])
        )

        vacancy_block = (
            vacancy_text[:1000]
            if vacancy_text
            else "Текст вакансии не передан. Не создавай замечание об отсутствии вакансии."
        )

        return f"""
    Важное правило для резюме:
    - Контактные данные являются обязательной частью резюме.
    - Никогда не рекомендуй удалять, скрывать, маскировать или не указывать e-mail и номер телефона.

        Верни только валидный JSON следующей структуры:

    {{
    "issues": [
        {{
        "severity": "Critical | Major | Minor",
        "issue_type": "short_snake_case_issue_type",
        "description": "описание замечания на русском языке",
        "evidence_fragment": "точный фрагмент из документа",
        "recommendation": "конкретная рекомендация на русском языке",
        "confidence_score": 0.0
        }}
    ]
    }}

    Правила:
    - Значение severity оставь строго одним из: Critical, Major, Minor.
    - Все остальные текстовые поля пиши на русском языке.
    - evidence_fragment заполняй только если такой фрагмент реально есть в тексте документа.
    - RAG-контекст является только справочной базой знаний, а не текстом проверяемого документа.
    - Не используй RAG-контекст как evidence_fragment.
    - Не создавай замечание только потому, что в RAG-контексте есть правило или пример ошибки.
    - evidence_fragment должен быть дословным фрагментом из блока «Текст документа».
    - Не включай персональные данные, если они не были маскированы.
    - Не принимай решение о найме.
    - Не оценивай кандидата как человека.
    - Проверяй только качество документа: структуру, ясность, конкретность, логичность и соответствие вакансии.
    - Если текст вакансии не передан, не создавай замечание об отсутствии вакансии.
    - Фраза вида «работал с Python», «работал с PostgreSQL», «работал с клиентами» не является ошибкой сама по себе.
    - Считай формулировку слабой только если она полностью общая и не содержит объекта, результата, технологии или контекста.
    - Не создавай замечание об отсутствии технологии, навыка или инструмента, если этот термин или его очевидный вариант написания встречается в тексте документа.
    - Если PostgreSQL, Docker, Docker Compose, FastAPI, Django, SQLAlchemy, Alembic, Redis, Nginx, Git, Linux или другая технология указана в навыках, проектах или опыте, считай требование подтверждённым.
    - Не требуй, чтобы технология обязательно находилась только в разделе опыта работы: разделы навыков и проектов тоже подтверждают наличие опыта.
    - Если замечаний нет, верни {{"issues": []}}.

    Тип документа:
    {document.metadata.document_type.value}

    Текст документа:
    {document_text}

    Текст вакансии:
    {vacancy_block}

    RAG-контекст:
    {rag_fragments}
    """.strip()

    def _parse_issues(
        self,
        parsed: dict,
        document_text: str,
    ) -> list[Issue]:
        raw_issues = parsed.get("issues", [])

        if not isinstance(raw_issues, list):
            return []

        issues: list[Issue] = []

        for raw_issue in raw_issues:
            if not isinstance(raw_issue, dict):
                continue

            issue = self._parse_issue(raw_issue)

            if issue is None:
                continue

            if self._issue_recommends_removing_contacts(issue):
                logger.info(
                    "llm_issue_filtered recommends_removing_contacts issue_type=%s description=%s recommendation=%s",
                    issue.issue_type,
                    issue.description,
                    issue.recommendation.recommendation_text,
                )
                continue

            if not self._issue_is_supported_by_document(
                issue=issue,
                document_text=document_text,
            ):
                logger.info(
                    "llm_issue_filtered unsupported_by_document issue_type=%s description=%s evidence=%s",
                    issue.issue_type,
                    issue.description,
                    issue.evidence_fragment,
                )
                continue

            if self._issue_contradicts_document_skills(
                issue=issue,
                document_text=document_text,
            ):
                logger.info(
                    "llm_issue_filtered contradicts_document_skills issue_type=%s description=%s evidence=%s",
                    issue.issue_type,
                    issue.description,
                    issue.evidence_fragment,
                )
                continue

            issues.append(issue)

        return issues

    @classmethod
    def _issue_recommends_removing_contacts(cls, issue: Issue) -> bool:
        issue_text = cls._normalize_for_match(
            " ".join(
                value
                for value in [
                    issue.issue_type,
                    issue.description,
                    issue.recommendation.recommendation_text,
                ]
                if value
            )
        )

        contact_markers = [
            "контакт",
            "email",
            "e mail",
            "телефон",
            "номер телефона",
            "персональные данные",
            "personal data",
            "contact details",
            "phone number",
        ]
        removal_markers = [
            "удал",
            "убрат",
            "исключ",
            "скрыт",
            "скрой",
            "маскиров",
            "не указыва",
            "не публику",
            "remove",
            "delete",
            "hide",
            "mask",
            "omit",
        ]

        return (
            any(marker in issue_text for marker in contact_markers)
            and any(marker in issue_text for marker in removal_markers)
        )

    def _parse_issue(self, raw_issue: dict) -> Issue | None:
        severity = self._parse_severity(
            str(raw_issue.get("severity", "Minor"))
        )

        issue_type = str(
            raw_issue.get("issue_type", "llm_semantic_issue")
        ).strip()

        description = str(
            raw_issue.get("description", "")
        ).strip()

        if not description:
            return None

        evidence_fragment = raw_issue.get("evidence_fragment")

        if evidence_fragment is not None:
            evidence_fragment = str(evidence_fragment).strip() or None

        recommendation_text = str(
            raw_issue.get("recommendation", "")
        ).strip()

        if not recommendation_text:
            recommendation_text = "Проверьте этот фрагмент документа вручную."

        confidence_score = self._parse_confidence(
            raw_issue.get("confidence_score", 0.5)
        )

        return Issue(
            issue_id=str(uuid4()),
            severity=severity,
            issue_type=issue_type,
            description=description,
            evidence_fragment=evidence_fragment,
            recommendation=Recommendation(
                recommendation_id=str(uuid4()),
                recommendation_text=recommendation_text,
                example_fix=None,
                priority_order=0,
            ),
            source_agent=self.agent_name,
            confidence_score=confidence_score,
            metadata={
                "llm_generated": True,
            },
        )

    @classmethod
    def _issue_is_supported_by_document(
        cls,
        issue: Issue,
        document_text: str,
    ) -> bool:
        """
        LLM не должен создавать замечание на основании RAG-контекста,
        вакансии или собственных предположений.

        """

        if not issue.evidence_fragment:
            return False

        normalized_evidence = cls._normalize_for_match(issue.evidence_fragment)
        normalized_document = cls._normalize_for_match(document_text)

        if not normalized_evidence:
            return False

        return normalized_evidence in normalized_document

    @classmethod
    def _issue_contradicts_document_skills(
        cls,
        issue: Issue,
        document_text: str,
    ) -> bool:
        """
        Отбрасывает ложные LLM-замечания вида:
        «PostgreSQL отсутствует», если PostgreSQL реально встречается
        в тексте резюме.
        """

        issue_text = cls._normalize_for_match(
            " ".join(
                value
                for value in [
                    issue.description,
                    issue.evidence_fragment or "",
                    (
                        issue.recommendation.recommendation_text
                        if issue.recommendation
                        else ""
                    ),
                ]
                if value
            )
        )

        absence_markers = [
            "отсутствует",
            "отсутствуют",
            "не найден",
            "не найдены",
            "нет ",
            "нету ",
            "missing",
            "not found",
            "absent",
        ]

        if not any(marker in issue_text for marker in absence_markers):
            return False

        normalized_document = VacancyRelevanceAgent._normalize_text(document_text)

        for skill in VacancyRelevanceAgent.IMPORTANT_SKILLS:
            skill_label = VacancyRelevanceAgent.SKILL_LABELS.get(skill, skill)
            normalized_skill = cls._normalize_for_match(skill)
            normalized_label = cls._normalize_for_match(skill_label)

            skill_is_mentioned_in_issue = (
                normalized_skill in issue_text
                or normalized_label in issue_text
            )

            if not skill_is_mentioned_in_issue:
                continue

            if VacancyRelevanceAgent._skill_is_present(
                skill=skill,
                normalized_text=normalized_document,
            ):
                return True

        return False

    @staticmethod
    def _normalize_for_match(text: str) -> str:
        normalized = text.lower()
        normalized = normalized.replace("ё", "е")
        normalized = normalized.replace("-", " ")
        normalized = normalized.replace("_", " ")
        normalized = normalized.replace("/", " ")
        normalized = normalized.replace("\\", " ")

        return " ".join(normalized.split())

    @staticmethod
    def _parse_severity(value: str) -> Severity:
        normalized = value.strip().lower()

        if normalized == "critical":
            return Severity.CRITICAL

        if normalized == "major":
            return Severity.MAJOR

        return Severity.MINOR

    @staticmethod
    def _parse_confidence(value) -> float:
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return 0.5

        return max(0.0, min(1.0, parsed))

    @staticmethod
    def _duration_ms(
        started_at: datetime,
        ended_at: datetime,
    ) -> float:
        return round(
            (ended_at - started_at).total_seconds() * 1000,
            3,
        )

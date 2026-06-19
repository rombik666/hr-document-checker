from datetime import datetime, timezone

from app.agents.semantic.llm_semantic_agent import LlmSemanticAgent
from app.schemas.common import DocumentType, ProcessingStatus, SourceFormat, StorageMode
from app.schemas.documents import DocumentMetadata, ParsedDocument
from app.schemas.rag import RagContext, RagSearchResult


def test_llm_semantic_agent_returns_llm_issue(monkeypatch) -> None:

    from app.core.config import settings

    monkeypatch.setattr(settings, "llm_provider", "mock")
    monkeypatch.setattr(settings, "llm_enabled", True)
    
    document = ParsedDocument(
        metadata=DocumentMetadata(
            document_id="llm-test-doc",
            document_type=DocumentType.CV,
            source_format=SourceFormat.DOCX,
            filename="resume.docx",
            upload_time=datetime.now(timezone.utc),
            processing_status=ProcessingStatus.PARSED,
            storage_mode=StorageMode.TEMPORARY,
        ),
        raw_text="Backend developer. Занимался разработкой backend. Навыки: Python, Git.",
        sections=[],
        entities=[],
    )

    rag_context = RagContext(
        query="cv quality",
        results=[
            RagSearchResult(
                chunk_id="chunk-1",
                source_id="source-1",
                title="CV quality",
                text="Good CV descriptions should include concrete achievements.",
                score=0.9,
                metadata={},
            )
        ],
    )

    result = LlmSemanticAgent().run(
        document=document,
        rag_context=rag_context,
        vacancy_text="Требования: Python, FastAPI, Docker.",
    )

    assert result.execution.agent_name == "LlmSemanticAgent"
    assert result.issues
    assert result.issues[0].metadata["llm_generated"] is True


def test_llm_semantic_agent_filters_recommendation_to_remove_contacts() -> None:
    issues = LlmSemanticAgent()._parse_issues(
        parsed={
            "issues": [
                {
                    "severity": "Minor",
                    "issue_type": "personal_data_in_resume",
                    "description": "Есть email и телефон в тексте резюме.",
                    "evidence_fragment": "Контакты: ivan@example.com, телефон +7 999 123-45-67.",
                    "recommendation": "Удалите контактные данные из резюме.",
                    "confidence_score": 0.9,
                }
            ]
        },
        document_text="Контакты: ivan@example.com, телефон +7 999 123-45-67.",
    )

    assert issues == []


def test_llm_semantic_agent_keeps_contact_format_recommendation() -> None:
    issues = LlmSemanticAgent()._parse_issues(
        parsed={
            "issues": [
                {
                    "severity": "Major",
                    "issue_type": "invalid_phone_format",
                    "description": "Номер телефона указан не полностью.",
                    "evidence_fragment": "Телефон: 12345.",
                    "recommendation": "Укажите полный номер телефона.",
                    "confidence_score": 0.9,
                }
            ]
        },
        document_text="Телефон: 12345.",
    )

    assert len(issues) == 1
    assert issues[0].issue_type == "invalid_phone_format"

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
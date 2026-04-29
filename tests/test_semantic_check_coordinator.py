from datetime import datetime, timezone

from app.coordinator.semantic_check_coordinator import SemanticCheckCoordinator
from app.schemas.common import DocumentType, ProcessingStatus, SourceFormat, StorageMode
from app.schemas.documents import DocumentMetadata, ParsedDocument


def test_semantic_check_coordinator_returns_issues() -> None:
    document = ParsedDocument(
        metadata=DocumentMetadata(
            document_id="test-doc",
            document_type=DocumentType.CV,
            source_format=SourceFormat.DOCX,
            filename="resume.docx",
            upload_time=datetime.now(timezone.utc),
            processing_status=ProcessingStatus.PARSED,
            storage_mode=StorageMode.TEMPORARY,
        ),
        raw_text=(
            "Backend developer. "
            "Занимался разработкой backend. "
            "Навыки: Python, Git."
        ),
        sections=[],
        entities=[],
    )

    vacancy_text = "Требования: Python, FastAPI, PostgreSQL, Docker, Git."

    response = SemanticCheckCoordinator().run(
        document=document,
        vacancy_text=vacancy_text,
    )

    agent_names = {
    item.execution.agent_name
    for item in response.check_results
}

    assert response.document_id == "test-doc"
    assert response.total_issues > 0
    assert len(response.check_results) == 3


def test_semantic_check_coordinator_can_run_llm_agent_when_enabled(monkeypatch) -> None:
    from datetime import datetime, timezone

    from app.coordinator.semantic_check_coordinator import SemanticCheckCoordinator
    from app.core.config import settings
    from app.schemas.common import (
        DocumentType,
        ProcessingStatus,
        SourceFormat,
        StorageMode,
    )
    from app.schemas.documents import DocumentMetadata, ParsedDocument

    monkeypatch.setattr(settings, "llm_provider", "mock")
    monkeypatch.setattr(settings, "llm_enabled", True)
    monkeypatch.setattr(settings, "llm_semantic_agent_enabled", True)

    document = ParsedDocument(
        metadata=DocumentMetadata(
            document_id="test-doc-llm-enabled",
            document_type=DocumentType.CV,
            source_format=SourceFormat.DOCX,
            filename="resume.docx",
            upload_time=datetime.now(timezone.utc),
            processing_status=ProcessingStatus.PARSED,
            storage_mode=StorageMode.TEMPORARY,
        ),
        raw_text=(
            "Backend developer. "
            "Занимался разработкой backend. "
            "Навыки: Python, Git."
        ),
        sections=[],
        entities=[],
    )

    response = SemanticCheckCoordinator(
        enable_llm_agent=True,
    ).run(
        document=document,
        vacancy_text="Требования: Python, FastAPI, PostgreSQL, Docker, Git.",
    )

    agent_names = {
        item.execution.agent_name
        for item in response.check_results
    }

    assert "LlmSemanticAgent" in agent_names
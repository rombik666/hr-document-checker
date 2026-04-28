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

    assert response.document_id == "test-doc"
    assert response.total_issues > 0
    assert len(response.check_results) == 3
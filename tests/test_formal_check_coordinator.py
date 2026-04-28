from datetime import datetime, timezone

from app.coordinator.formal_check_coordinator import FormalCheckCoordinator
from app.schemas.common import DocumentType, ProcessingStatus, SourceFormat, StorageMode
from app.schemas.documents import DocumentMetadata, DocumentSection, ParsedDocument


def test_formal_check_coordinator_returns_summary() -> None:
    document = ParsedDocument(
        metadata=DocumentMetadata(
            document_id="test-doc",
            document_type=DocumentType.UNKNOWN,
            source_format=SourceFormat.DOCX,
            filename="resume.docx",
            upload_time=datetime.now(timezone.utc),
            processing_status=ProcessingStatus.PARSED,
            storage_mode=StorageMode.TEMPORARY,
        ),
        raw_text="Короткое резюме без контактов",
        sections=[
            DocumentSection(
                section_id="section-1",
                section_type="unknown",
                title=None,
                text="Короткое резюме без контактов",
                position_in_document=0,
            )
        ],
        entities=[],
    )

    response = FormalCheckCoordinator().run(document)

    assert response.document_id == "test-doc"
    assert response.filename == "resume.docx"
    assert response.total_issues > 0
    assert len(response.check_results) == 4
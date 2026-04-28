from datetime import datetime, timezone

from app.agents.formal.contact_validation_agent import ContactValidationAgent
from app.schemas.common import DocumentType, EntityType, ProcessingStatus, SourceFormat, StorageMode
from app.schemas.documents import DocumentMetadata, ExtractedEntity, ParsedDocument


def make_document_with_entities(entities: list[ExtractedEntity]) -> ParsedDocument:
    return ParsedDocument(
        metadata=DocumentMetadata(
            document_id="test-doc",
            document_type=DocumentType.UNKNOWN,
            source_format=SourceFormat.DOCX,
            filename="resume.docx",
            upload_time=datetime.now(timezone.utc),
            processing_status=ProcessingStatus.PARSED,
            storage_mode=StorageMode.TEMPORARY,
        ),
        raw_text="",
        sections=[],
        entities=entities,
    )


def test_contact_validation_agent_detects_duplicated_email() -> None:
    document = make_document_with_entities(
        [
            ExtractedEntity(
                entity_id="1",
                entity_type=EntityType.EMAIL,
                value="ivan@example.com",
                normalized_value="ivan@example.com",
            ),
            ExtractedEntity(
                entity_id="2",
                entity_type=EntityType.EMAIL,
                value="IVAN@example.com",
                normalized_value="ivan@example.com",
            ),
        ]
    )

    result = ContactValidationAgent().run(document)

    issue_types = {issue.issue_type for issue in result.issues}

    assert "duplicated_email" in issue_types
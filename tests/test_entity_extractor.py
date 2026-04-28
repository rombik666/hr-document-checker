from datetime import datetime, timezone

from app.extractors.entity_extractor import EntityExtractor
from app.schemas.common import DocumentType, EntityType, ProcessingStatus, SourceFormat, StorageMode
from app.schemas.documents import DocumentMetadata, DocumentSection, ParsedDocument


def test_entity_extractor_enriches_parsed_document() -> None:
    text = """
    Иван Иванов
    Email: ivan@example.com
    Телефон: +7 999 123-45-67
    GitHub: https://github.com/ivan

    Навыки: Python, FastAPI, PostgreSQL, Docker
    Опыт работы: 2020-2023
    """

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
        raw_text=text,
        sections=[
            DocumentSection(
                section_id="section-1",
                section_type="paragraph",
                title=None,
                text=text,
                position_in_document=0,
            )
        ],
        entities=[],
    )

    extractor = EntityExtractor()
    enriched_document = extractor.enrich(document)

    entity_types = {entity.entity_type for entity in enriched_document.entities}
    skills = {entity.normalized_value for entity in enriched_document.entities if entity.entity_type == EntityType.SKILL}

    assert EntityType.EMAIL in entity_types
    assert EntityType.PHONE in entity_types
    assert EntityType.URL in entity_types
    assert EntityType.DATE in entity_types
    assert EntityType.SKILL in entity_types

    assert "python" in skills
    assert "fastapi" in skills
    assert "postgresql" in skills
    assert "docker" in skills
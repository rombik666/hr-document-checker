from datetime import datetime, timezone

from app.agents.formal.completeness_agent import CompletenessAgent
from app.schemas.common import DocumentType, EntityType, ProcessingStatus, SourceFormat, StorageMode
from app.schemas.documents import DocumentMetadata, DocumentSection, ExtractedEntity, ParsedDocument


def make_document(
    raw_text: str,
    section_types: list[str],
    entities: list[ExtractedEntity],
) -> ParsedDocument:
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
        raw_text=raw_text,
        sections=[
            DocumentSection(
                section_id=f"section-{index}",
                section_type=section_type,
                title=None,
                text=section_type,
                position_in_document=index,
            )
            for index, section_type in enumerate(section_types)
        ],
        entities=entities,
    )


def make_entity(entity_type: EntityType, value: str) -> ExtractedEntity:
    return ExtractedEntity(
        entity_id=value,
        entity_type=entity_type,
        value=value,
        normalized_value=value.lower(),
    )


def test_completeness_agent_detects_missing_contacts() -> None:
    document = make_document(
        raw_text="Опыт работы: Python-разработчик",
        section_types=["experience"],
        entities=[],
    )

    result = CompletenessAgent().run(document)

    issue_types = {issue.issue_type for issue in result.issues}

    assert "missing_contacts" in issue_types
    assert "missing_email" in issue_types
    assert "missing_phone" in issue_types


def test_completeness_agent_accepts_document_with_contacts_and_sections() -> None:
    document = make_document(
        raw_text="Резюме",
        section_types=["contacts", "experience", "skills", "education"],
        entities=[
            make_entity(EntityType.EMAIL, "ivan@example.com"),
            make_entity(EntityType.PHONE, "+79991234567"),
            make_entity(EntityType.SKILL, "python"),
        ],
    )

    result = CompletenessAgent().run(document)

    issue_types = {issue.issue_type for issue in result.issues}

    assert "missing_contacts" not in issue_types
    assert "missing_email" not in issue_types
    assert "missing_phone" not in issue_types
    assert "missing_experience_section" not in issue_types
    assert "missing_skills_section" not in issue_types
    assert "missing_education_section" not in issue_types
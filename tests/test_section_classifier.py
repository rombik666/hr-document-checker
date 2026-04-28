from datetime import datetime, timezone

from app.extractors.section_classifier import SectionClassifier
from app.schemas.common import DocumentType, ProcessingStatus, SourceFormat, StorageMode
from app.schemas.documents import DocumentMetadata, DocumentSection, ParsedDocument


def make_document_with_section(text: str) -> ParsedDocument:
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


def test_section_classifier_detects_contacts() -> None:
    document = make_document_with_section("Контакты: ivan@example.com, +7 999 123-45-67")

    classifier = SectionClassifier()
    classified_document = classifier.classify(document)

    assert classified_document.sections[0].section_type == "contacts"
    assert classified_document.sections[0].metadata["original_section_type"] == "paragraph"


def test_section_classifier_detects_experience() -> None:
    document = make_document_with_section("Опыт работы: Python-разработчик в компании")

    classifier = SectionClassifier()
    classified_document = classifier.classify(document)

    assert classified_document.sections[0].section_type == "experience"


def test_section_classifier_returns_unknown_for_unrecognized_text() -> None:
    document = make_document_with_section("Просто какой-то текст без заголовков")

    classifier = SectionClassifier()
    classified_document = classifier.classify(document)

    assert classified_document.sections[0].section_type == "unknown"
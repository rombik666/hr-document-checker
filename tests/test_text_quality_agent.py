from datetime import datetime, timezone

from app.agents.semantic.text_quality_agent import TextQualityAgent
from app.schemas.common import DocumentType, ProcessingStatus, SourceFormat, StorageMode
from app.schemas.documents import DocumentMetadata, ParsedDocument


def make_document(text: str) -> ParsedDocument:
    return ParsedDocument(
        metadata=DocumentMetadata(
            document_id="test-doc",
            document_type=DocumentType.CV,
            source_format=SourceFormat.DOCX,
            filename="resume.docx",
            upload_time=datetime.now(timezone.utc),
            processing_status=ProcessingStatus.PARSED,
            storage_mode=StorageMode.TEMPORARY,
        ),
        raw_text=text,
        sections=[],
        entities=[],
    )


def test_text_quality_agent_detects_weak_phrase() -> None:
    document = make_document("Занимался разработкой backend.")

    result = TextQualityAgent().run(document)

    issue_types = {issue.issue_type for issue in result.issues}

    assert "weak_phrase" in issue_types


def test_text_quality_agent_detects_water_phrase() -> None:
    document = make_document("Ответственный, коммуникабельный, быстро обучаюсь.")

    result = TextQualityAgent().run(document)

    issue_types = {issue.issue_type for issue in result.issues}

    assert "weak_phrase" in issue_types
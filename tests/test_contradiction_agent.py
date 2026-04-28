from datetime import datetime, timezone

from app.agents.semantic.contradiction_agent import ContradictionAgent
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


def test_contradiction_agent_detects_backend_without_backend_skills() -> None:
    document = make_document("Backend developer. Опыт работы 2022-2024.")

    result = ContradictionAgent().run(document)

    issue_types = {issue.issue_type for issue in result.issues}

    assert "backend_role_without_backend_skills" in issue_types


def test_contradiction_agent_detects_senior_with_short_experience() -> None:
    document = make_document("Senior Python developer. Опыт работы 2023-2024.")

    result = ContradictionAgent().run(document)

    issue_types = {issue.issue_type for issue in result.issues}

    assert "possible_senior_experience_mismatch" in issue_types
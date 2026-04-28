from datetime import datetime, timezone

from app.agents.semantic.vacancy_relevance_agent import VacancyRelevanceAgent
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


def test_vacancy_relevance_agent_detects_missing_skills() -> None:
    document = make_document("Навыки: Python, Git")

    vacancy_text = "Требования: Python, FastAPI, PostgreSQL, Docker, Git."

    result = VacancyRelevanceAgent().run(
        document=document,
        vacancy_text=vacancy_text,
    )

    assert len(result.issues) == 1

    issue = result.issues[0]

    assert issue.issue_type == "vacancy_requirements_gap"
    assert "fastapi" in issue.metadata["missing_skills"]
    assert "postgresql" in issue.metadata["missing_skills"]
    assert "docker" in issue.metadata["missing_skills"]
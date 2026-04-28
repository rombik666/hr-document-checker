from pathlib import Path

from docx import Document
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_report_endpoint_returns_report_for_valid_docx(tmp_path: Path) -> None:
    file_path = tmp_path / "resume.docx"

    document = Document()
    document.add_paragraph("Контакты:")
    document.add_paragraph("Email: ivan@example.com")
    document.add_paragraph("Телефон: +7 999 123-45-67")
    document.add_paragraph("Навыки: Python, FastAPI, PostgreSQL")
    document.add_paragraph("Опыт работы: Python-разработчик, 2021-2024")
    document.add_paragraph("Образование: Южный федеральный университет")
    document.save(file_path)

    with file_path.open("rb") as file:
        response = client.post(
            "/api/v1/documents/report",
            files={
                "file": (
                    "resume.docx",
                    file,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )

    assert response.status_code == 200

    data = response.json()

    assert data["filename"] == "resume.docx"
    assert data["summary_status"] == "ready"
    assert data["total_issues"] == 0

    assert data["critical"] == []
    assert data["major"] == []
    assert data["minor"] == []

    assert data["technical_info"]["total_agents_count"] == 4
    assert data["technical_info"]["metadata"]["document_type"] == "cv"
    assert "CompletenessAgent" in data["technical_info"]["checks_completed"]


def test_report_endpoint_rejects_unsupported_file_format(tmp_path: Path) -> None:
    file_path = tmp_path / "resume.txt"
    file_path.write_text("Simple text file", encoding="utf-8")

    with file_path.open("rb") as file:
        response = client.post(
            "/api/v1/documents/report",
            files={
                "file": (
                    "resume.txt",
                    file,
                    "text/plain",
                )
            },
        )

    assert response.status_code == 400

    data = response.json()

    assert "Поддерживаются только файлы .docx и .pdf" in data["detail"]
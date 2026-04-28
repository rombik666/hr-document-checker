from pathlib import Path

from docx import Document
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_web_index_page_returns_upload_form() -> None:
    response = client.get("/web/")

    assert response.status_code == 200
    assert "Проверка HR-документа" in response.text
    assert "storage_mode" in response.text
    assert "Документ DOCX/PDF" in response.text


def test_web_report_page_returns_html_report(tmp_path: Path) -> None:
    file_path = tmp_path / "resume.docx"

    document = Document()
    document.add_paragraph("Контакты:")
    document.add_paragraph("Email: ivan@example.com")
    document.add_paragraph("Телефон: +7 999 123-45-67")
    document.add_paragraph("Навыки: Python, Git")
    document.add_paragraph("Опыт работы:")
    document.add_paragraph("Backend developer, 2023-2024")
    document.add_paragraph("Занимался разработкой backend.")
    document.add_paragraph("Образование: Южный федеральный университет")
    document.save(file_path)

    with file_path.open("rb") as file:
        response = client.post(
            "/web/report",
            data={
                "vacancy_text": "Требования: Python, FastAPI, PostgreSQL, Docker, Git.",
                "storage_mode": "no_store",
            },
            files={
                "file": (
                    "resume.docx",
                    file,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )

    assert response.status_code == 200
    assert "Итоговый отчёт" in response.text
    assert "resume.docx" in response.text
    assert "weak_phrase" in response.text
    assert "vacancy_requirements_gap" in response.text
    assert "fastapi" in response.text
    assert "no_store" in response.text


def test_web_report_rejects_unsupported_file_format(tmp_path: Path) -> None:
    file_path = tmp_path / "resume.txt"
    file_path.write_text("Simple text", encoding="utf-8")

    with file_path.open("rb") as file:
        response = client.post(
            "/web/report",
            data={
                "storage_mode": "temporary",
            },
            files={
                "file": (
                    "resume.txt",
                    file,
                    "text/plain",
                )
            },
        )

    assert response.status_code == 400
    assert "Поддерживаются только файлы .docx и .pdf" in response.text
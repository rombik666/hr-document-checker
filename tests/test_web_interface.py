from pathlib import Path

from docx import Document
from fastapi.testclient import TestClient

from app.main import app
from tests.auth_helpers import auth_headers


client = TestClient(app)


def test_web_index_redirects_anonymous_user_to_login_page() -> None:
    response = client.get("/web/")

    assert response.status_code == 200
    assert "Вход в систему" in response.text
    assert "Создать учётную запись" in response.text


def test_web_dashboard_returns_candidate_dashboard_for_authenticated_user() -> None:
    response = client.get(
        "/web/dashboard",
        headers=auth_headers(client, "candidate"),
    )

    assert response.status_code == 200
    assert "Кабинет кандидата" in response.text
    assert "Проверить резюме" in response.text


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
            headers=auth_headers(client, "candidate"),
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
    assert "Результат проверки" in response.text
    assert "Всего замечаний" in response.text
    assert "Новая проверка" in response.text


def test_web_report_rejects_unsupported_file_format(tmp_path: Path) -> None:
    file_path = tmp_path / "resume.txt"
    file_path.write_text("Simple text", encoding="utf-8")

    with file_path.open("rb") as file:
        response = client.post(
            "/web/report",
            headers=auth_headers(client, "candidate"),
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
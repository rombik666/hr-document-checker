from pathlib import Path

from docx import Document
from fastapi.testclient import TestClient

from app.main import app
from tests.auth_helpers import auth_headers

from sqlalchemy import delete

from app.db.models import RagSourceORM
from app.db.session import SessionLocal


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

def test_web_reports_history_requires_authentication() -> None:
    anonymous_client = TestClient(app)

    response = anonymous_client.get(
        "/web/reports",
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/web/login"


def test_web_reports_history_returns_authenticated_user_reports() -> None:
    response = client.get(
        "/web/reports",
        headers=auth_headers(client, "candidate"),
    )

    assert response.status_code == 200
    assert "История проверок" in response.text


def test_web_saved_report_page_returns_html_report(tmp_path: Path) -> None:
    file_path = tmp_path / "saved_resume.docx"

    document = Document()
    document.add_paragraph("Контакты:")
    document.add_paragraph("Email: ivan@example.com")
    document.add_paragraph("Телефон: +7 999 123-45-67")
    document.add_paragraph("Навыки: Python, Git")
    document.add_paragraph("Опыт работы: Backend developer, 2023-2024")
    document.add_paragraph("Образование: Южный федеральный университет")
    document.save(file_path)

    headers = auth_headers(client, "candidate")

    with file_path.open("rb") as file:
        create_response = client.post(
            "/web/report",
            headers=headers,
            data={
                "vacancy_text": "Требования: Python, FastAPI, PostgreSQL, Docker, Git.",
                "storage_mode": "temporary",
            },
            files={
                "file": (
                    "saved_resume.docx",
                    file,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )

    assert create_response.status_code == 200

    # report_id есть в ссылках HTML-страницы результата.
    marker = "/web/reports/"
    assert marker in create_response.text

    report_id = create_response.text.split(marker, maxsplit=1)[1].split('"', maxsplit=1)[0]

    saved_response = client.get(
        f"/web/reports/{report_id}",
        headers=headers,
    )

    assert saved_response.status_code == 200
    assert "Результат проверки" in saved_response.text
    assert "Скачать DOCX" in saved_response.text
    assert "Релевантность вакансии" in saved_response.text

def _cleanup_web_rag_sources() -> None:
    db = SessionLocal()

    try:
        db.execute(
            delete(RagSourceORM).where(
                RagSourceORM.filename.like("%web_rag_ui_test%")
            )
        )
        db.commit()
    finally:
        db.close()


def test_web_rag_sources_requires_authentication() -> None:
    anonymous_client = TestClient(app)

    response = anonymous_client.get(
        "/web/rag/sources",
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/web/login"


def test_web_rag_sources_forbids_candidate() -> None:
    response = client.get(
        "/web/rag/sources",
        headers=auth_headers(client, "candidate"),
    )

    assert response.status_code == 403
    assert "RAG-источники доступны только HR-специалистам" in response.text


def test_web_rag_sources_page_returns_hr_ui() -> None:
    response = client.get(
        "/web/rag/sources",
        headers=auth_headers(client, "hr"),
    )

    assert response.status_code == 200
    assert "RAG-источники компании" in response.text
    assert "Загрузить источник" in response.text
    assert "Загруженные источники" in response.text


def test_web_hr_can_upload_rag_source(tmp_path: Path) -> None:
    _cleanup_web_rag_sources()

    headers = auth_headers(client, "hr")
    file_path = tmp_path / "web_rag_ui_test_requirements.txt"

    file_path.write_text(
        "Требования компании: Python, FastAPI, PostgreSQL, Docker.",
        encoding="utf-8",
    )

    try:
        with file_path.open("rb") as file:
            response = client.post(
                "/web/rag/sources/upload",
                headers=headers,
                data={
                    "title": "Web RAG UI source",
                    "source_type": "requirements",
                },
                files={
                    "file": (
                        file_path.name,
                        file,
                        "text/plain",
                    )
                },
            )

        assert response.status_code == 200
        assert "RAG-источник успешно загружен" in response.text
        assert "Web RAG UI source" in response.text
        assert "web_rag_ui_test_requirements.txt" in response.text

    finally:
        _cleanup_web_rag_sources()


def test_web_hr_can_deactivate_rag_source(tmp_path: Path) -> None:
    _cleanup_web_rag_sources()

    headers = auth_headers(client, "hr")
    file_path = tmp_path / "web_rag_ui_test_delete.txt"

    file_path.write_text(
        "Источник для отключения через Web UI.",
        encoding="utf-8",
    )

    try:
        with file_path.open("rb") as file:
            upload_response = client.post(
                "/web/rag/sources/upload",
                headers=headers,
                data={
                    "title": "Web RAG UI delete source",
                    "source_type": "other",
                },
                files={
                    "file": (
                        file_path.name,
                        file,
                        "text/plain",
                    )
                },
            )

        assert upload_response.status_code == 200

        db = SessionLocal()

        try:
            source = (
                db.query(RagSourceORM)
                .filter(RagSourceORM.filename == "web_rag_ui_test_delete.txt")
                .one()
            )

            source_id = source.id

        finally:
            db.close()

        delete_response = client.post(
            f"/web/rag/sources/{source_id}/delete",
            headers=headers,
        )

        assert delete_response.status_code == 200
        assert "RAG-источник отключён" in delete_response.text
        assert "inactive" in delete_response.text

    finally:
        _cleanup_web_rag_sources()


def test_web_rag_source_upload_rejects_unsupported_format(tmp_path: Path) -> None:
    headers = auth_headers(client, "hr")
    file_path = tmp_path / "web_rag_ui_test_bad.exe"

    file_path.write_text("bad file", encoding="utf-8")

    with file_path.open("rb") as file:
        response = client.post(
            "/web/rag/sources/upload",
            headers=headers,
            data={
                "title": "Bad source",
                "source_type": "other",
            },
            files={
                "file": (
                    file_path.name,
                    file,
                    "application/octet-stream",
                )
            },
        )

    assert response.status_code == 400
    assert "Поддерживаются только RAG-источники" in response.text
from pathlib import Path

from docx import Document
from fastapi.testclient import TestClient

from app.main import app
from tests.auth_helpers import admin_auth_headers, auth_headers


client = TestClient(app)


def test_user_cannot_read_another_users_report(tmp_path: Path) -> None:
    file_path = tmp_path / "resume.docx"

    document = Document()
    document.add_paragraph("Контакты:")
    document.add_paragraph("Email: ivan@example.com")
    document.add_paragraph("Телефон: +7 999 123-45-67")
    document.add_paragraph("Навыки: Python, FastAPI, PostgreSQL")
    document.add_paragraph("Опыт работы: Python-разработчик, 2021-2024")
    document.add_paragraph("Образование: Южный федеральный университет")
    document.save(file_path)

    owner_headers = auth_headers(client, "candidate")
    another_user_headers = auth_headers(client, "candidate")

    with file_path.open("rb") as file:
        create_response = client.post(
            "/api/v1/documents/report",
            headers=owner_headers,
            data={
                "storage_mode": "temporary",
            },
            files={
                "file": (
                    "resume.docx",
                    file,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )

    assert create_response.status_code == 200

    report_id = create_response.json()["report_id"]

    owner_response = client.get(
        f"/api/v1/documents/reports/{report_id}",
        headers=owner_headers,
    )

    assert owner_response.status_code == 200

    another_user_response = client.get(
        f"/api/v1/documents/reports/{report_id}",
        headers=another_user_headers,
    )

    assert another_user_response.status_code == 404


def test_admin_can_read_any_report(tmp_path: Path) -> None:
    file_path = tmp_path / "resume.docx"

    document = Document()
    document.add_paragraph("Контакты:")
    document.add_paragraph("Email: ivan@example.com")
    document.add_paragraph("Телефон: +7 999 123-45-67")
    document.add_paragraph("Навыки: Python, FastAPI, PostgreSQL")
    document.add_paragraph("Опыт работы: Python-разработчик, 2021-2024")
    document.add_paragraph("Образование: Южный федеральный университет")
    document.save(file_path)

    owner_headers = auth_headers(client, "candidate")

    with file_path.open("rb") as file:
        create_response = client.post(
            "/api/v1/documents/report",
            headers=owner_headers,
            data={
                "storage_mode": "temporary",
            },
            files={
                "file": (
                    "resume.docx",
                    file,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )

    assert create_response.status_code == 200

    report_id = create_response.json()["report_id"]

    admin_response = client.get(
        f"/api/v1/documents/reports/{report_id}",
        headers=admin_auth_headers(client),
    )

    assert admin_response.status_code == 200
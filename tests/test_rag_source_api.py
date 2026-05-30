from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db.models import RagSourceORM
from app.db.session import SessionLocal
from app.main import app
from tests.auth_helpers import admin_auth_headers, auth_headers

from io import BytesIO


client = TestClient(app)


def _cleanup_rag_sources() -> None:
    db = SessionLocal()

    try:
        db.execute(
            delete(RagSourceORM).where(
                RagSourceORM.filename.like("%rag_api_test%")
            )
        )
        db.commit()
    finally:
        db.close()


def test_hr_can_upload_and_list_own_rag_source(tmp_path: Path) -> None:
    _cleanup_rag_sources()

    file_path = tmp_path / "rag_api_test_vacancy.txt"
    file_path.write_text(
        "Вакансия Backend Python. Требования: Python, FastAPI, PostgreSQL, Docker.",
        encoding="utf-8",
    )

    headers = auth_headers(client, "hr")

    try:
        with file_path.open("rb") as file:
            upload_response = client.post(
                "/api/v1/rag/sources/upload",
                headers=headers,
                data={
                    "title": "Backend vacancy",
                    "source_type": "vacancy",
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

        upload_data = upload_response.json()
        source = upload_data["source"]

        assert source["source_id"]
        assert source["title"] == "Backend vacancy"
        assert source["source_type"] == "vacancy"
        assert source["source_format"] == "txt"
        assert source["is_active"] is True
        assert "FastAPI" in source["content"]
        assert "PostgreSQL" in source["content"]

        list_response = client.get(
            "/api/v1/rag/sources",
            headers=headers,
        )

        assert list_response.status_code == 200

        list_data = list_response.json()
        source_ids = {
            item["source_id"]
            for item in list_data["sources"]
        }

        assert source["source_id"] in source_ids

    finally:
        _cleanup_rag_sources()


def test_hr_cannot_access_another_hr_rag_source(tmp_path: Path) -> None:
    _cleanup_rag_sources()

    first_headers = auth_headers(client, "hr")
    second_headers = auth_headers(client, "hr")

    file_path = tmp_path / "rag_api_test_private.txt"
    file_path.write_text(
        "Внутренний источник первого HR.",
        encoding="utf-8",
    )

    try:
        with file_path.open("rb") as file:
            upload_response = client.post(
                "/api/v1/rag/sources/upload",
                headers=first_headers,
                data={
                    "title": "Private HR source",
                    "source_type": "policy",
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
        source_id = upload_response.json()["source"]["source_id"]

        forbidden_response = client.get(
            f"/api/v1/rag/sources/{source_id}",
            headers=second_headers,
        )

        assert forbidden_response.status_code == 404

        second_list_response = client.get(
            "/api/v1/rag/sources",
            headers=second_headers,
        )

        assert second_list_response.status_code == 200

        second_source_ids = {
            item["source_id"]
            for item in second_list_response.json()["sources"]
        }

        assert source_id not in second_source_ids

    finally:
        _cleanup_rag_sources()


def test_admin_can_access_any_rag_source(tmp_path: Path) -> None:
    _cleanup_rag_sources()

    hr_headers = auth_headers(client, "hr")

    file_path = tmp_path / "rag_api_test_admin_visible.txt"
    file_path.write_text(
        "Источник HR, видимый администратору.",
        encoding="utf-8",
    )

    try:
        with file_path.open("rb") as file:
            upload_response = client.post(
                "/api/v1/rag/sources/upload",
                headers=hr_headers,
                data={
                    "title": "Admin visible source",
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
        source_id = upload_response.json()["source"]["source_id"]

        admin_response = client.get(
            f"/api/v1/rag/sources/{source_id}",
            headers=admin_auth_headers(client),
        )

        assert admin_response.status_code == 200
        assert admin_response.json()["source_id"] == source_id

    finally:
        _cleanup_rag_sources()


def test_candidate_cannot_manage_rag_sources(tmp_path: Path) -> None:
    file_path = tmp_path / "rag_api_test_candidate.txt"
    file_path.write_text(
        "Кандидат не должен загружать корпоративный RAG-источник.",
        encoding="utf-8",
    )

    headers = auth_headers(client, "candidate")

    with file_path.open("rb") as file:
        upload_response = client.post(
            "/api/v1/rag/sources/upload",
            headers=headers,
            data={
                "title": "Candidate source",
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

    list_response = client.get(
        "/api/v1/rag/sources",
        headers=headers,
    )

    assert upload_response.status_code == 403
    assert list_response.status_code == 403


def test_hr_can_deactivate_own_rag_source(tmp_path: Path) -> None:
    _cleanup_rag_sources()

    headers = auth_headers(client, "hr")

    file_path = tmp_path / "rag_api_test_deactivate.txt"
    file_path.write_text(
        "Источник для деактивации.",
        encoding="utf-8",
    )

    try:
        with file_path.open("rb") as file:
            upload_response = client.post(
                "/api/v1/rag/sources/upload",
                headers=headers,
                data={
                    "title": "Deactivate source",
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
        source_id = upload_response.json()["source"]["source_id"]

        delete_response = client.delete(
            f"/api/v1/rag/sources/{source_id}",
            headers=headers,
        )

        assert delete_response.status_code == 200
        assert delete_response.json()["deleted"] is True

        active_list_response = client.get(
            "/api/v1/rag/sources",
            headers=headers,
        )

        active_ids = {
            item["source_id"]
            for item in active_list_response.json()["sources"]
        }

        assert source_id not in active_ids

        inactive_list_response = client.get(
            "/api/v1/rag/sources?include_inactive=true",
            headers=headers,
        )

        inactive_ids = {
            item["source_id"]
            for item in inactive_list_response.json()["sources"]
        }

        assert source_id in inactive_ids

    finally:
        _cleanup_rag_sources()


def test_rag_source_upload_rejects_unsupported_format(tmp_path: Path) -> None:
    file_path = tmp_path / "rag_api_test_source.exe"
    file_path.write_text("bad file", encoding="utf-8")

    headers = auth_headers(client, "hr")

    with file_path.open("rb") as file:
        response = client.post(
            "/api/v1/rag/sources/upload",
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
    assert "Unsupported RAG source format" in response.json()["detail"]

def test_rag_source_upload_rejects_file_larger_than_15_mb() -> None:
    headers = auth_headers(client, "hr")

    oversized_content = b"x" * (15 * 1024 * 1024 + 1)

    response = client.post(
        "/api/v1/rag/sources/upload",
        headers=headers,
        data={
            "title": "Oversized source",
            "source_type": "other",
        },
        files={
            "file": (
                "oversized_rag_source.txt",
                BytesIO(oversized_content),
                "text/plain",
            )
        },
    )

    assert response.status_code == 413
    assert "Maximum allowed file size is 15 MB" in response.json()["detail"]


def test_rag_source_upload_rejects_user_storage_quota_exceeded(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _cleanup_rag_sources()

    monkeypatch.setattr(
        "app.services.rag_source_service.RagSourceService.MAX_USER_STORAGE_BYTES",
        100,
    )

    headers = auth_headers(client, "hr")

    first_file = tmp_path / "rag_api_test_quota_first.txt"
    first_file.write_text("x" * 80, encoding="utf-8")

    second_file = tmp_path / "rag_api_test_quota_second.txt"
    second_file.write_text("x" * 30, encoding="utf-8")

    try:
        with first_file.open("rb") as file:
            first_response = client.post(
                "/api/v1/rag/sources/upload",
                headers=headers,
                data={
                    "title": "Quota first source",
                    "source_type": "other",
                },
                files={
                    "file": (
                        first_file.name,
                        file,
                        "text/plain",
                    )
                },
            )

        assert first_response.status_code == 200
        assert first_response.json()["source"]["file_size_bytes"] == 80

        with second_file.open("rb") as file:
            second_response = client.post(
                "/api/v1/rag/sources/upload",
                headers=headers,
                data={
                    "title": "Quota second source",
                    "source_type": "other",
                },
                files={
                    "file": (
                        second_file.name,
                        file,
                        "text/plain",
                    )
                },
            )

        assert second_response.status_code == 400
        assert "storage quota exceeded" in second_response.json()["detail"]

    finally:
        _cleanup_rag_sources()

def test_hr_can_activate_deactivated_rag_source(tmp_path: Path) -> None:
    _cleanup_rag_sources()

    headers = auth_headers(client, "hr")

    file_path = tmp_path / "rag_api_test_activate.txt"
    file_path.write_text(
        "Источник для повторного включения.",
        encoding="utf-8",
    )

    try:
        with file_path.open("rb") as file:
            upload_response = client.post(
                "/api/v1/rag/sources/upload",
                headers=headers,
                data={
                    "title": "Activate source",
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
        source_id = upload_response.json()["source"]["source_id"]

        deactivate_response = client.delete(
            f"/api/v1/rag/sources/{source_id}",
            headers=headers,
        )

        assert deactivate_response.status_code == 200

        activate_response = client.post(
            f"/api/v1/rag/sources/{source_id}/activate",
            headers=headers,
        )

        assert activate_response.status_code == 200
        assert activate_response.json()["success"] is True
        assert activate_response.json()["action"] == "activate"

        details_response = client.get(
            f"/api/v1/rag/sources/{source_id}",
            headers=headers,
        )

        assert details_response.status_code == 200
        assert details_response.json()["is_active"] is True

    finally:
        _cleanup_rag_sources()


def test_hr_can_permanently_delete_own_rag_source(tmp_path: Path) -> None:
    _cleanup_rag_sources()

    headers = auth_headers(client, "hr")

    file_path = tmp_path / "rag_api_test_permanent_delete.txt"
    file_path.write_text(
        "Источник для полного удаления.",
        encoding="utf-8",
    )

    try:
        with file_path.open("rb") as file:
            upload_response = client.post(
                "/api/v1/rag/sources/upload",
                headers=headers,
                data={
                    "title": "Permanent delete source",
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
        source_id = upload_response.json()["source"]["source_id"]

        delete_response = client.delete(
            f"/api/v1/rag/sources/{source_id}/permanent",
            headers=headers,
        )

        assert delete_response.status_code == 200
        assert delete_response.json()["success"] is True
        assert delete_response.json()["action"] == "permanent_delete"

        details_response = client.get(
            f"/api/v1/rag/sources/{source_id}",
            headers=headers,
        )

        assert details_response.status_code == 404

    finally:
        _cleanup_rag_sources()
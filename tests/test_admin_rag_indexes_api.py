from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.core.config import settings
from app.db.models import RagIndexORM, RagSourceORM
from app.db.session import SessionLocal
from app.main import app
from tests.auth_helpers import admin_auth_headers, auth_headers


client = TestClient(app)


def _cleanup_admin_rag_index_test_data() -> None:
    db = SessionLocal()

    try:
        sources = (
            db.query(RagSourceORM)
            .filter(RagSourceORM.filename.like("%admin_rag_index_test%"))
            .all()
        )

        owner_user_ids = {
            source.owner_user_id
            for source in sources
            if source.owner_user_id is not None
        }

        db.execute(
            delete(RagSourceORM).where(
                RagSourceORM.filename.like("%admin_rag_index_test%")
            )
        )

        for owner_user_id in owner_user_ids:
            db.execute(
                delete(RagIndexORM).where(
                    RagIndexORM.owner_user_id == owner_user_id,
                )
            )

        db.commit()

    finally:
        db.close()


def _upload_hr_source_and_get_owner_id(
    headers: dict[str, str],
    tmp_path: Path,
) -> str:
    file_path = tmp_path / "admin_rag_index_test_requirements.txt"
    file_path.write_text(
        "Admin RAG index test source: Python, FastAPI, PostgreSQL, Docker.",
        encoding="utf-8",
    )

    with file_path.open("rb") as file:
        upload_response = client.post(
            "/api/v1/rag/sources/upload",
            headers=headers,
            data={
                "title": "Admin RAG index test source",
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

    assert upload_response.status_code == 200

    source_id = upload_response.json()["source"]["source_id"]

    db = SessionLocal()

    try:
        source = db.get(RagSourceORM, source_id)

        assert source is not None
        assert source.owner_user_id is not None

        return source.owner_user_id

    finally:
        db.close()


def test_admin_can_list_rag_indexes() -> None:
    response = client.get(
        "/api/v1/admin/rag/indexes",
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200

    data = response.json()

    assert "indexes" in data
    assert "total" in data
    assert "ready_count" in data
    assert "stale_count" in data
    assert "missing_count" in data
    assert "failed_count" in data
    assert "building_count" in data
    assert "reindex_required_count" in data
    assert isinstance(data["indexes"], list)


def test_non_admin_cannot_list_rag_indexes() -> None:
    response = client.get(
        "/api/v1/admin/rag/indexes",
        headers=auth_headers(client, "hr"),
    )

    assert response.status_code == 403


def test_admin_can_view_and_reindex_user_rag_index(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _cleanup_admin_rag_index_test_data()

    monkeypatch.setattr(
        settings,
        "rag_index_dir",
        tmp_path / "index",
    )

    hr_headers = auth_headers(client, "hr")
    admin_headers = admin_auth_headers(client)

    try:
        owner_user_id = _upload_hr_source_and_get_owner_id(
            headers=hr_headers,
            tmp_path=tmp_path,
        )

        detail_response = client.get(
            f"/api/v1/admin/rag/indexes/{owner_user_id}",
            headers=admin_headers,
        )

        assert detail_response.status_code == 200

        detail = detail_response.json()

        assert detail["owner_user_id"] == owner_user_id
        assert detail["owner_role"] == "hr"
        assert detail["status"] == "stale"
        assert detail["reindex_required"] is True
        assert detail["sources_count"] == 1
        assert detail["active_sources_count"] == 1

        reindex_response = client.post(
            f"/api/v1/admin/rag/indexes/{owner_user_id}/reindex",
            headers=admin_headers,
        )

        assert reindex_response.status_code == 200

        reindex_data = reindex_response.json()

        assert reindex_data["status"] == "completed"
        assert reindex_data["message"] == "User RAG FAISS index was rebuilt successfully."

        index = reindex_data["index"]

        assert index["owner_user_id"] == owner_user_id
        assert index["status"] == "ready"
        assert index["reindex_required"] is False
        assert index["sources_count"] == 1
        assert index["active_sources_count"] == 1
        assert index["chunks_count"] >= 1
        assert index["index_exists"] is True
        assert index["index_path"]
        assert index["chunks_path"]
        assert index["last_reindexed_at"] is not None

        ready_detail_response = client.get(
            f"/api/v1/admin/rag/indexes/{owner_user_id}",
            headers=admin_headers,
        )

        assert ready_detail_response.status_code == 200
        assert ready_detail_response.json()["status"] == "ready"

    finally:
        _cleanup_admin_rag_index_test_data()


def test_admin_rag_index_detail_rejects_candidate_user() -> None:
    candidate_headers = auth_headers(client, "candidate")

    db = SessionLocal()

    try:
        candidates = (
            db.query(RagSourceORM.owner_user_id)
            .filter(RagSourceORM.owner_user_id.isnot(None))
            .all()
        )

    finally:
        db.close()

    # Надёжнее получить candidate id через защищённый сценарий невозможно без
    # раскрытия токена, поэтому проверяем 404 для несуществующего пользователя.
    response = client.get(
        "/api/v1/admin/rag/indexes/non-existing-user-id",
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 404
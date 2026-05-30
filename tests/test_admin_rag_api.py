from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db.models import RagSourceORM
from app.db.session import SessionLocal
from app.main import app
from tests.auth_helpers import admin_auth_headers, auth_headers


client = TestClient(app)


def _cleanup_rag_sources() -> None:
    db = SessionLocal()

    try:
        db.execute(
            delete(RagSourceORM).where(
                RagSourceORM.filename.like("%admin_rag_api_test%")
            )
        )
        db.commit()
    finally:
        db.close()


def _upload_text_rag_source(
    headers: dict[str, str],
    tmp_path: Path,
    filename: str,
    content: str,
    title: str,
    source_type: str = "requirements",
) -> str:
    file_path = tmp_path / filename
    file_path.write_text(content, encoding="utf-8")

    with file_path.open("rb") as file:
        response = client.post(
            "/api/v1/rag/sources/upload",
            headers=headers,
            data={
                "title": title,
                "source_type": source_type,
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

    return response.json()["source"]["source_id"]


def test_admin_rag_sources_returns_db_source_metadata(tmp_path: Path) -> None:
    _cleanup_rag_sources()

    hr_headers = auth_headers(client, "hr")
    source_ids: list[str] = []

    try:
        source_id = _upload_text_rag_source(
            headers=hr_headers,
            tmp_path=tmp_path,
            filename="admin_rag_api_test_requirements.txt",
            title="Admin RAG API source",
            content="DB-backed RAG source for admin metadata test.",
            source_type="requirements",
        )
        source_ids.append(source_id)

        response = client.get(
            "/api/v1/admin/rag/sources",
            headers=admin_auth_headers(client),
        )

        assert response.status_code == 200

        data = response.json()

        assert data["knowledge_base_dir"] == "database://rag_sources"
        assert data["sources_count"] >= 1

        matching_sources = [
            item
            for item in data["sources"]
            if item["source_id"] == source_id
        ]

        assert len(matching_sources) == 1

        source = matching_sources[0]

        assert source["title"] == "Admin RAG API source"
        assert source["path"] == f"db://rag_sources/{source_id}"
        assert source["content_length"] > 0
        assert "content" not in source

    finally:
        _cleanup_rag_sources()


def test_admin_rag_reindex_returns_not_required_for_db_backed_rag(tmp_path: Path) -> None:
    _cleanup_rag_sources()

    hr_headers = auth_headers(client, "hr")

    try:
        _upload_text_rag_source(
            headers=hr_headers,
            tmp_path=tmp_path,
            filename="admin_rag_api_test_reindex.txt",
            title="Admin RAG API reindex source",
            content=(
                "DB-backed RAG uses dynamic in-memory retrieval. "
                "FAISS reindex is not required."
            ),
            source_type="policy",
        )

        response = client.post(
            "/api/v1/admin/rag/reindex",
            headers=admin_auth_headers(client),
        )

        assert response.status_code == 200

        data = response.json()

        assert data["status"] == "not_required"
        assert data["mode"] == "db_sources"
        assert data["source_backend"] == "database"
        assert data["sources_count"] >= 1
        assert data["active_sources_count"] >= 1
        assert data["chunks_count"] >= 1
        assert data["embedding_dimension"] is not None
        assert data["index_path"] is None
        assert data["chunks_path"] is None
        assert "FAISS reindex is not required" in data["message"]

    finally:
        _cleanup_rag_sources()


def test_admin_rag_status_returns_db_backed_status(tmp_path: Path) -> None:
    _cleanup_rag_sources()

    hr_headers = auth_headers(client, "hr")

    try:
        _upload_text_rag_source(
            headers=hr_headers,
            tmp_path=tmp_path,
            filename="admin_rag_api_test_status.txt",
            title="Admin RAG API status source",
            content="DB-backed RAG status source with Python and FastAPI.",
            source_type="requirements",
        )

        response = client.get(
            "/api/v1/admin/rag/status",
            headers=admin_auth_headers(client),
        )

        assert response.status_code == 200

        data = response.json()

        assert data["mode"] == "db_sources"
        assert data["source_backend"] == "database"
        assert data["user_scope"] == "all"
        assert data["knowledge_base_dir"] is None
        assert data["sources_count"] >= 1
        assert data["active_sources_count"] >= 1
        assert data["chunks_count"] >= 1
        assert data["index_dir"] is None
        assert data["index_exists"] is False
        assert data["reindex_required"] is False

    finally:
        _cleanup_rag_sources()


def test_admin_rag_endpoints_forbid_non_admin_user() -> None:
    headers = auth_headers(client, role="candidate")

    sources_response = client.get(
        "/api/v1/admin/rag/sources",
        headers=headers,
    )

    reindex_response = client.post(
        "/api/v1/admin/rag/reindex",
        headers=headers,
    )

    status_response = client.get(
        "/api/v1/admin/rag/status",
        headers=headers,
    )

    assert sources_response.status_code == 403
    assert reindex_response.status_code == 403
    assert status_response.status_code == 403
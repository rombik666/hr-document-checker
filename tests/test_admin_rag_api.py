from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.core.config import settings
from app.db.models import RagIndexORM, RagSourceORM
from app.db.session import SessionLocal
from app.main import app
from tests.auth_helpers import admin_auth_headers, auth_headers


client = TestClient(app)


def _cleanup_rag_sources() -> None:
    db = SessionLocal()

    try:
        sources = (
            db.query(RagSourceORM)
            .filter(RagSourceORM.filename.like("%admin_rag_api_test%"))
            .all()
        )

        owner_user_ids = {
            source.owner_user_id
            for source in sources
            if source.owner_user_id is not None
        }

        db.execute(
            delete(RagSourceORM).where(
                RagSourceORM.filename.like("%admin_rag_api_test%")
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
            content="Per-user FAISS RAG source for admin metadata test.",
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


def test_admin_rag_reindex_rebuilds_admin_personal_faiss_index(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _cleanup_rag_sources()

    monkeypatch.setattr(
        settings,
        "rag_index_dir",
        tmp_path / "index",
    )

    admin_headers = admin_auth_headers(client)

    try:
        _upload_text_rag_source(
            headers=admin_headers,
            tmp_path=tmp_path,
            filename="admin_rag_api_test_reindex.txt",
            title="Admin RAG API reindex source",
            content=(
                "Per-user FAISS RAG uses explicit reindex. "
                "Admin own index can be rebuilt through admin endpoint."
            ),
            source_type="policy",
        )

        response = client.post(
            "/api/v1/admin/rag/reindex",
            headers=admin_headers,
        )

        assert response.status_code == 200

        data = response.json()

        assert data["status"] == "completed"
        assert data["mode"] == "per_user_faiss"
        assert data["source_backend"] == "database+filesystem"
        assert data["sources_count"] >= 1
        assert data["active_sources_count"] >= 1
        assert data["chunks_count"] >= 1
        assert data["embedding_dimension"] is not None
        assert data["index_path"]
        assert data["chunks_path"]
        assert "FAISS index was rebuilt" in data["message"]

        assert Path(data["index_path"]).exists()
        assert Path(data["chunks_path"]).exists()

    finally:
        _cleanup_rag_sources()


def test_admin_rag_status_returns_personal_faiss_status(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _cleanup_rag_sources()

    monkeypatch.setattr(
        settings,
        "rag_index_dir",
        tmp_path / "index",
    )

    admin_headers = admin_auth_headers(client)

    try:
        _upload_text_rag_source(
            headers=admin_headers,
            tmp_path=tmp_path,
            filename="admin_rag_api_test_status.txt",
            title="Admin RAG API status source",
            content="Per-user FAISS RAG status source with Python and FastAPI.",
            source_type="requirements",
        )

        response = client.get(
            "/api/v1/admin/rag/status",
            headers=admin_headers,
        )

        assert response.status_code == 200

        data = response.json()

        assert data["mode"] == "per_user_faiss"
        assert data["source_backend"] == "database+filesystem"
        assert data["user_scope"] == "current_user"
        assert data["knowledge_base_dir"] is not None

        assert data["sources_count"] >= 1
        assert data["active_sources_count"] >= 1
        assert data["inactive_sources_count"] >= 0
        assert data["chunks_count"] == 0

        assert data["retriever_type"] == "faiss"
        assert data["embedding_dimension"] is not None
        assert data["embedding_backend"] is not None
        assert data["embedding_model_name"] is not None

        assert data["index_dir"] is not None
        assert data["index_exists"] is False
        assert data["reindex_required"] is True
        assert data["index_status"] == "stale"
        assert data["index_owner_user_id"]
        assert data["index_path"]
        assert data["chunks_path"]
        assert data["sources_hash"]
        assert data["last_reindexed_at"] is None
        assert data["index_error"] is None

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

    indexes_response = client.get(
        "/api/v1/admin/rag/indexes",
        headers=headers,
    )

    unknown_index_response = client.get(
        "/api/v1/admin/rag/indexes/non-existing-user-id",
        headers=headers,
    )

    unknown_index_reindex_response = client.post(
        "/api/v1/admin/rag/indexes/non-existing-user-id/reindex",
        headers=headers,
    )

    assert sources_response.status_code == 403
    assert reindex_response.status_code == 403
    assert status_response.status_code == 403
    assert indexes_response.status_code == 403
    assert unknown_index_response.status_code == 403
    assert unknown_index_reindex_response.status_code == 403
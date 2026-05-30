from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.core.config import settings
from app.db.models import RagIndexORM, RagIndexStatus, RagSourceORM
from app.db.session import SessionLocal
from app.main import app
from tests.auth_helpers import auth_headers


client = TestClient(app)


def _cleanup_reindex_test_data() -> None:
    db = SessionLocal()

    try:
        sources = (
            db.query(RagSourceORM)
            .filter(RagSourceORM.filename.like("%rag_reindex_api_test%"))
            .all()
        )

        owner_user_ids = {
            source.owner_user_id
            for source in sources
            if source.owner_user_id is not None
        }

        for owner_user_id in owner_user_ids:
            db.execute(
                delete(RagIndexORM).where(
                    RagIndexORM.owner_user_id == owner_user_id,
                )
            )

        db.execute(
            delete(RagSourceORM).where(
                RagSourceORM.filename.like("%rag_reindex_api_test%")
            )
        )

        db.commit()

    finally:
        db.close()


def test_hr_can_reindex_own_uploaded_rag_sources(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _cleanup_reindex_test_data()

    monkeypatch.setattr(
        settings,
        "rag_index_dir",
        tmp_path / "index",
    )

    headers = auth_headers(client, "hr")

    file_path = tmp_path / "rag_reindex_api_test_vacancy.txt"
    file_path.write_text(
        "Вакансия Backend Python. "
        "Требования: Python, FastAPI, PostgreSQL, Docker. "
        "Будет плюсом опыт с Docker Compose и REST API.",
        encoding="utf-8",
    )

    try:
        with file_path.open("rb") as file:
            upload_response = client.post(
                "/api/v1/rag/sources/upload",
                headers=headers,
                data={
                    "title": "RAG reindex API test vacancy",
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
        source_id = upload_data["source"]["source_id"]

        db = SessionLocal()

        try:
            source = db.get(RagSourceORM, source_id)

            assert source is not None
            assert source.owner_user_id is not None

            stale_index = (
                db.query(RagIndexORM)
                .filter(RagIndexORM.owner_user_id == source.owner_user_id)
                .one_or_none()
            )

            assert stale_index is not None
            assert stale_index.status == RagIndexStatus.STALE.value
            assert stale_index.reindex_required is True

        finally:
            db.close()

        reindex_response = client.post(
            "/api/v1/rag/reindex",
            headers=headers,
        )

        assert reindex_response.status_code == 200

        data = reindex_response.json()

        assert data["status"] == "completed"
        assert data["message"] == "Personal RAG FAISS index was rebuilt successfully."
        assert data["owner_user_id"]
        assert data["sources_count"] == 1
        assert data["chunks_count"] >= 1
        assert data["index_path"]
        assert data["chunks_path"]
        assert data["sources_hash"]
        assert data["reindex_required"] is False
        assert data["embedding_backend"] == settings.rag_embedding_backend
        assert data["embedding_dimension"] == settings.rag_embedding_dimension
        assert data["retriever_type"] == "faiss"
        assert data["last_reindexed_at"] is not None

        assert Path(data["index_path"]).exists()
        assert Path(data["chunks_path"]).exists()

        db = SessionLocal()

        try:
            source = db.get(RagSourceORM, source_id)

            assert source is not None
            assert source.owner_user_id is not None

            ready_index = (
                db.query(RagIndexORM)
                .filter(RagIndexORM.owner_user_id == source.owner_user_id)
                .one()
            )

            assert ready_index.status == RagIndexStatus.READY.value
            assert ready_index.reindex_required is False
            assert ready_index.sources_count == 1
            assert ready_index.chunks_count >= 1
            assert ready_index.index_path == data["index_path"]
            assert ready_index.chunks_path == data["chunks_path"]
            assert ready_index.last_reindexed_at is not None
            assert ready_index.error_message is None

        finally:
            db.close()

    finally:
        _cleanup_reindex_test_data()


def test_hr_can_reindex_empty_rag_sources(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        settings,
        "rag_index_dir",
        tmp_path / "index",
    )

    headers = auth_headers(client, "hr")

    reindex_response = client.post(
        "/api/v1/rag/reindex",
        headers=headers,
    )

    assert reindex_response.status_code == 200

    data = reindex_response.json()

    assert data["status"] == "completed"
    assert data["sources_count"] == 0
    assert data["chunks_count"] == 0
    assert data["reindex_required"] is False
    assert data["index_path"]
    assert data["chunks_path"]

    assert Path(data["index_path"]).exists()
    assert Path(data["chunks_path"]).exists()


def test_candidate_cannot_reindex_rag_sources() -> None:
    headers = auth_headers(client, "candidate")

    response = client.post(
        "/api/v1/rag/reindex",
        headers=headers,
    )

    assert response.status_code == 403
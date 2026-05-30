from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.core.config import settings
from app.db.models import RagIndexORM, RagSourceORM
from app.db.session import SessionLocal
from app.main import app
from tests.auth_helpers import auth_headers


client = TestClient(app)


def _cleanup_search_test_data() -> None:
    db = SessionLocal()

    try:
        sources = (
            db.query(RagSourceORM)
            .filter(RagSourceORM.filename.like("%rag_search_api_test%"))
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
                RagSourceORM.filename.like("%rag_search_api_test%")
            )
        )

        db.commit()

    finally:
        db.close()


def test_rag_search_before_reindex_returns_409(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _cleanup_search_test_data()

    monkeypatch.setattr(
        settings,
        "rag_index_dir",
        tmp_path / "index",
    )

    headers = auth_headers(client, "hr")

    file_path = tmp_path / "rag_search_api_test_before_reindex.txt"
    file_path.write_text(
        "Вакансия Backend Python. Требования: Python, FastAPI, PostgreSQL.",
        encoding="utf-8",
    )

    try:
        with file_path.open("rb") as file:
            upload_response = client.post(
                "/api/v1/rag/sources/upload",
                headers=headers,
                data={
                    "title": "Search before reindex source",
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

        search_response = client.post(
            "/api/v1/rag/search",
            headers=headers,
            json={
                "query": "Python FastAPI PostgreSQL",
                "top_k": 3,
            },
        )

        assert search_response.status_code == 409

        detail = search_response.json()["detail"]

        assert detail["error"] == "rag_reindex_required"
        assert detail["index_status"] == "stale"
        assert detail["reindex_required"] is True
        assert detail["sources_count"] == 1

    finally:
        _cleanup_search_test_data()


def test_rag_search_after_reindex_returns_faiss_results(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _cleanup_search_test_data()

    monkeypatch.setattr(
        settings,
        "rag_index_dir",
        tmp_path / "index",
    )

    headers = auth_headers(client, "hr")

    file_path = tmp_path / "rag_search_api_test_after_reindex.txt"
    file_path.write_text(
        "Вакансия Backend Python. "
        "Требования: Python, FastAPI, PostgreSQL, Docker. "
        "Нужен опыт разработки REST API и контейнеризации.",
        encoding="utf-8",
    )

    try:
        with file_path.open("rb") as file:
            upload_response = client.post(
                "/api/v1/rag/sources/upload",
                headers=headers,
                data={
                    "title": "Search after reindex source",
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

        reindex_response = client.post(
            "/api/v1/rag/reindex",
            headers=headers,
        )

        assert reindex_response.status_code == 200
        assert reindex_response.json()["reindex_required"] is False

        search_response = client.post(
            "/api/v1/rag/search",
            headers=headers,
            json={
                "query": "Python FastAPI PostgreSQL Docker REST API",
                "top_k": 3,
            },
        )

        assert search_response.status_code == 200

        data = search_response.json()

        assert data["query"] == "Python FastAPI PostgreSQL Docker REST API"
        assert len(data["results"]) >= 1

        first_result = data["results"][0]

        assert first_result["source_id"]
        assert first_result["title"] == "Search after reindex source"
        assert "FastAPI" in first_result["text"]
        assert first_result["score"] > 0
        assert first_result["metadata"]["retriever"] == "FaissVectorStore"

    finally:
        _cleanup_search_test_data()


def test_rag_search_after_source_change_requires_reindex(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _cleanup_search_test_data()

    monkeypatch.setattr(
        settings,
        "rag_index_dir",
        tmp_path / "index",
    )

    headers = auth_headers(client, "hr")

    first_file = tmp_path / "rag_search_api_test_first.txt"
    first_file.write_text(
        "Первый источник: Python, FastAPI, PostgreSQL.",
        encoding="utf-8",
    )

    second_file = tmp_path / "rag_search_api_test_second.txt"
    second_file.write_text(
        "Второй источник: Docker, CI/CD, Linux.",
        encoding="utf-8",
    )

    try:
        with first_file.open("rb") as file:
            first_upload_response = client.post(
                "/api/v1/rag/sources/upload",
                headers=headers,
                data={
                    "title": "First search source",
                    "source_type": "vacancy",
                },
                files={
                    "file": (
                        first_file.name,
                        file,
                        "text/plain",
                    )
                },
            )

        assert first_upload_response.status_code == 200

        reindex_response = client.post(
            "/api/v1/rag/reindex",
            headers=headers,
        )

        assert reindex_response.status_code == 200

        search_response = client.post(
            "/api/v1/rag/search",
            headers=headers,
            json={
                "query": "Python FastAPI",
                "top_k": 3,
            },
        )

        assert search_response.status_code == 200

        with second_file.open("rb") as file:
            second_upload_response = client.post(
                "/api/v1/rag/sources/upload",
                headers=headers,
                data={
                    "title": "Second search source",
                    "source_type": "vacancy",
                },
                files={
                    "file": (
                        second_file.name,
                        file,
                        "text/plain",
                    )
                },
            )

        assert second_upload_response.status_code == 200

        stale_search_response = client.post(
            "/api/v1/rag/search",
            headers=headers,
            json={
                "query": "Docker Linux",
                "top_k": 3,
            },
        )

        assert stale_search_response.status_code == 409

        detail = stale_search_response.json()["detail"]

        assert detail["error"] == "rag_reindex_required"
        assert detail["index_status"] == "stale"
        assert detail["reindex_required"] is True
        assert detail["sources_count"] == 2

    finally:
        _cleanup_search_test_data()
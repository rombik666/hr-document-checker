from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.core.config import settings
from app.db.models import RagIndexORM, RagSourceORM
from app.db.session import SessionLocal
from app.main import app
from tests.auth_helpers import admin_auth_headers, auth_headers


client = TestClient(app)


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


def _reindex(headers: dict[str, str]) -> dict:
    response = client.post(
        "/api/v1/rag/reindex",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "completed"
    assert data["reindex_required"] is False
    assert data["index_path"]
    assert data["chunks_path"]

    return data


def _delete_sources(source_ids: list[str]) -> None:
    db = SessionLocal()

    try:
        owner_user_ids: set[str] = set()

        if source_ids:
            sources = (
                db.query(RagSourceORM)
                .filter(RagSourceORM.id.in_(source_ids))
                .all()
            )

            owner_user_ids.update(
                source.owner_user_id
                for source in sources
                if source.owner_user_id is not None
            )

            db.execute(
                delete(RagSourceORM).where(
                    RagSourceORM.id.in_(source_ids)
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


def _result_text(response_json: dict) -> str:
    return "\n".join(
        item["text"]
        for item in response_json["results"]
    ).lower()


def test_hr_without_uploaded_sources_gets_empty_rag_context_after_reindex(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        settings,
        "rag_index_dir",
        tmp_path / "index",
    )

    headers = auth_headers(client, "hr")

    _reindex(headers)

    response = client.post(
        "/api/v1/rag/search",
        headers=headers,
        json={
            "query": "Kafka Redis Kubernetes",
            "top_k": 3,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["query"] == "Kafka Redis Kubernetes"
    assert data["results"] == []


def test_hr_search_uses_uploaded_rag_source_after_reindex(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        settings,
        "rag_index_dir",
        tmp_path / "index",
    )

    headers = auth_headers(client, "hr")
    source_ids: list[str] = []

    try:
        source_id = _upload_text_rag_source(
            headers=headers,
            tmp_path=tmp_path,
            filename="rag_search_uploaded_backend_requirements.txt",
            title="RAG search test backend requirements",
            content=(
                "Корпоративные требования к backend-вакансии: "
                "кандидат должен знать Kafka, Redis, Kubernetes, "
                "а также иметь опыт разработки REST API."
            ),
        )
        source_ids.append(source_id)

        stale_response = client.post(
            "/api/v1/rag/search",
            headers=headers,
            json={
                "query": "Kafka Redis Kubernetes",
                "top_k": 3,
            },
        )

        assert stale_response.status_code == 409
        assert stale_response.json()["detail"]["error"] == "rag_reindex_required"

        _reindex(headers)

        response = client.post(
            "/api/v1/rag/search",
            headers=headers,
            json={
                "query": "Kafka Redis Kubernetes",
                "top_k": 3,
            },
        )

        assert response.status_code == 200

        data = response.json()

        assert data["query"] == "Kafka Redis Kubernetes"
        assert len(data["results"]) >= 1

        text = _result_text(data)

        assert "kafka" in text
        assert "redis" in text
        assert "kubernetes" in text

        source_ids_from_results = {
            item["source_id"]
            for item in data["results"]
        }

        assert source_id in source_ids_from_results

    finally:
        _delete_sources(source_ids)


def test_hr_search_does_not_use_another_hr_uploaded_source_after_reindex(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        settings,
        "rag_index_dir",
        tmp_path / "index",
    )

    first_hr_headers = auth_headers(client, "hr")
    second_hr_headers = auth_headers(client, "hr")
    source_ids: list[str] = []

    try:
        source_id = _upload_text_rag_source(
            headers=first_hr_headers,
            tmp_path=tmp_path,
            filename="rag_search_uploaded_private_source.txt",
            title="RAG search test private source",
            content=(
                "Закрытый источник первого HR: "
                "уникальные требования включают Apache Flink, ClickHouse, RabbitMQ."
            ),
        )
        source_ids.append(source_id)

        _reindex(first_hr_headers)
        _reindex(second_hr_headers)

        response = client.post(
            "/api/v1/rag/search",
            headers=second_hr_headers,
            json={
                "query": "Apache Flink ClickHouse RabbitMQ",
                "top_k": 3,
            },
        )

        assert response.status_code == 200

        data = response.json()

        assert data["query"] == "Apache Flink ClickHouse RabbitMQ"
        assert data["results"] == []

    finally:
        _delete_sources(source_ids)


def test_admin_search_uses_own_uploaded_rag_sources_after_reindex(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        settings,
        "rag_index_dir",
        tmp_path / "index",
    )

    admin_headers = admin_auth_headers(client)
    source_ids: list[str] = []

    try:
        source_id = _upload_text_rag_source(
            headers=admin_headers,
            tmp_path=tmp_path,
            filename="rag_search_uploaded_admin_own_source.txt",
            title="RAG search test admin own source",
            content=(
                "Источник администратора для проверки персонального индекса: "
                "требования включают Elasticsearch, Logstash, Kibana."
            ),
        )
        source_ids.append(source_id)

        _reindex(admin_headers)

        response = client.post(
            "/api/v1/rag/search",
            headers=admin_headers,
            json={
                "query": "Elasticsearch Logstash Kibana",
                "top_k": 3,
            },
        )

        assert response.status_code == 200

        data = response.json()

        assert len(data["results"]) >= 1

        text = _result_text(data)

        assert "elasticsearch" in text
        assert "logstash" in text
        assert "kibana" in text

        source_ids_from_results = {
            item["source_id"]
            for item in data["results"]
        }

        assert source_id in source_ids_from_results

    finally:
        _delete_sources(source_ids)


def test_deactivated_uploaded_source_is_not_used_in_rag_search_after_reindex(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        settings,
        "rag_index_dir",
        tmp_path / "index",
    )

    headers = auth_headers(client, "hr")
    source_ids: list[str] = []

    try:
        source_id = _upload_text_rag_source(
            headers=headers,
            tmp_path=tmp_path,
            filename="rag_search_uploaded_inactive_source.txt",
            title="RAG search test inactive source",
            content=(
                "Источник для деактивации: "
                "уникальные требования включают Snowflake, Airflow, dbt."
            ),
        )
        source_ids.append(source_id)

        _reindex(headers)

        active_response = client.post(
            "/api/v1/rag/search",
            headers=headers,
            json={
                "query": "Snowflake Airflow dbt",
                "top_k": 3,
            },
        )

        assert active_response.status_code == 200
        assert len(active_response.json()["results"]) >= 1

        delete_response = client.delete(
            f"/api/v1/rag/sources/{source_id}",
            headers=headers,
        )

        assert delete_response.status_code == 200

        stale_response = client.post(
            "/api/v1/rag/search",
            headers=headers,
            json={
                "query": "Snowflake Airflow dbt",
                "top_k": 3,
            },
        )

        assert stale_response.status_code == 409
        assert stale_response.json()["detail"]["error"] == "rag_reindex_required"

        _reindex(headers)

        response = client.post(
            "/api/v1/rag/search",
            headers=headers,
            json={
                "query": "Snowflake Airflow dbt",
                "top_k": 3,
            },
        )

        assert response.status_code == 200

        data = response.json()

        assert data["results"] == []

    finally:
        _delete_sources(source_ids)
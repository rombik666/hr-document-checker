from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.rag import RagSource
from tests.auth_helpers import admin_auth_headers, auth_headers


client = TestClient(app)


def test_admin_rag_sources_returns_source_metadata(monkeypatch) -> None:
    def fake_load_sources(self, knowledge_base_dir: Path):
        return [
            RagSource(
                source_id="source-1",
                title="hr_requirements",
                path=str(knowledge_base_dir / "hr_requirements.txt"),
                content="Тестовый источник базы знаний.",
            )
        ]

    monkeypatch.setattr(
        "app.rag.knowledge_loader.KnowledgeLoader.load_sources",
        fake_load_sources,
    )

    response = client.get(
        "/api/v1/admin/rag/sources",
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["sources_count"] == 1
    assert data["sources"][0]["source_id"] == "source-1"
    assert data["sources"][0]["title"] == "hr_requirements"
    assert data["sources"][0]["content_length"] > 0
    assert "content" not in data["sources"][0]


def test_admin_rag_reindex_returns_build_result(monkeypatch) -> None:
    def fake_build(self):
        return {
            "knowledge_base_dir": "data/knowledge_base",
            "index_dir": "data/index",
            "sources_count": 2,
            "chunks_count": 5,
            "embedding_dimension": 384,
            "index_path": "data/index/faiss.index",
            "chunks_path": "data/index/chunks.json",
        }

    monkeypatch.setattr(
        "app.rag.index_builder.RagIndexBuilder.build",
        fake_build,
    )

    response = client.post(
        "/api/v1/admin/rag/reindex",
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "completed"
    assert data["sources_count"] == 2
    assert data["chunks_count"] == 5
    assert data["embedding_dimension"] == 384
    assert data["index_path"] == "data/index/faiss.index"
    assert data["chunks_path"] == "data/index/chunks.json"


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
from pathlib import Path

from app.rag.service import RagService
from app.schemas.rag import RagSearchRequest


def test_rag_service_searches_temp_knowledge_base(tmp_path: Path) -> None:
    knowledge_base_dir = tmp_path / "knowledge_base"
    knowledge_base_dir.mkdir()

    file_path = knowledge_base_dir / "rules.md"
    file_path.write_text(
        "Python backend developer должен знать FastAPI, PostgreSQL и Docker.",
        encoding="utf-8",
    )

    service = RagService(knowledge_base_dir=knowledge_base_dir)

    context = service.search(
        RagSearchRequest(
            query="python fastapi docker",
            top_k=3,
        )
    )

    assert context.query == "python fastapi docker"
    assert len(context.results) >= 1
    assert "FastAPI" in context.results[0].text
from app.rag.faiss_store import FaissVectorStore
from app.rag.index_builder import RagIndexBuilder


def test_rag_index_builder_creates_faiss_index(tmp_path) -> None:
    knowledge_base_dir = tmp_path / "knowledge_base"
    index_dir = tmp_path / "index"

    knowledge_base_dir.mkdir()

    source_path = knowledge_base_dir / "rules.md"
    source_path.write_text(
        "# Python CV\n\nPython backend developer should mention FastAPI, PostgreSQL and Docker.",
        encoding="utf-8",
    )

    builder = RagIndexBuilder(
        knowledge_base_dir=knowledge_base_dir,
        index_dir=index_dir,
    )

    result = builder.build()

    assert result["sources_count"] == 1
    assert result["chunks_count"] >= 1
    assert FaissVectorStore.index_exists(index_dir)
from app.rag.retriever import SimpleRagRetriever
from app.schemas.rag import RagChunk


def test_simple_rag_retriever_returns_relevant_chunk() -> None:
    chunks = [
        RagChunk(
            chunk_id="1",
            source_id="source-1",
            title="python",
            text="Python backend developer должен знать FastAPI PostgreSQL Docker",
            position=0,
        ),
        RagChunk(
            chunk_id="2",
            source_id="source-2",
            title="cover_letter",
            text="Сопроводительное письмо должно быть кратким и привязанным к вакансии",
            position=1,
        ),
    ]

    retriever = SimpleRagRetriever()

    results = retriever.search(
        query="python fastapi docker",
        chunks=chunks,
        top_k=1,
    )

    assert len(results) == 1
    assert results[0].chunk_id == "1"
    assert results[0].score > 0
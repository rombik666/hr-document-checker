from app.rag.embedding_model import HashingEmbeddingModel
from app.rag.vector_store import InMemoryVectorStore
from app.schemas.rag import RagChunk


def test_in_memory_vector_store_returns_relevant_chunk() -> None:
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

    model = HashingEmbeddingModel(dimension=128)

    vector_store = InMemoryVectorStore.from_chunks(
        chunks=chunks,
        embedding_model=model,
    )

    results = vector_store.search(
        query="python fastapi docker",
        embedding_model=model,
        top_k=1,
    )

    assert len(results) == 1
    assert results[0].chunk_id == "1"
    assert results[0].score > 0
    assert results[0].metadata["retriever"] == "InMemoryVectorStore"
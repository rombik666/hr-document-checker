import numpy as np

from app.rag.embedding_model import EmbeddingModel
from app.schemas.rag import RagChunk, RagSearchResult


class InMemoryVectorStore:

    def __init__(
        self,
        chunks: list[RagChunk],
        embeddings: np.ndarray,
    ) -> None:
        self.chunks = chunks
        self.embeddings = embeddings

    @classmethod
    def from_chunks(
        cls,
        chunks: list[RagChunk],
        embedding_model: EmbeddingModel,
    ) -> "InMemoryVectorStore":
        texts = [
            chunk.text
            for chunk in chunks
        ]

        embeddings = embedding_model.embed_texts(texts)

        return cls(
            chunks=chunks,
            embeddings=embeddings,
        )

    def search(
        self,
        query: str,
        embedding_model: EmbeddingModel,
        top_k: int = 3,
    ) -> list[RagSearchResult]:
        if not self.chunks or self.embeddings.size == 0:
            return []

        query_embedding = embedding_model.embed_text(query)

        if np.linalg.norm(query_embedding) == 0:
            return []

        scores = self.embeddings @ query_embedding

        sorted_indices = np.argsort(scores)[::-1]

        results: list[RagSearchResult] = []

        for index in sorted_indices[:top_k]:
            score = float(scores[index])

            if score <= 0:
                continue

            chunk = self.chunks[int(index)]

            results.append(
                RagSearchResult(
                    chunk_id=chunk.chunk_id,
                    source_id=chunk.source_id,
                    title=chunk.title,
                    text=chunk.text,
                    score=round(score, 4),
                    metadata={
                        **chunk.metadata,
                        "retriever": "InMemoryVectorStore",
                    },
                )
            )

        return results
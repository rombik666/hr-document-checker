import json
from pathlib import Path

import faiss
import numpy as np

from app.rag.embedding_model import EmbeddingModel
from app.schemas.rag import RagChunk, RagSearchResult


class FaissVectorStore:

    INDEX_FILENAME = "faiss.index"
    CHUNKS_FILENAME = "chunks.json"

    def __init__(
        self,
        chunks: list[RagChunk],
        index: faiss.Index,
        index_dir: Path,
    ) -> None:
        self.chunks = chunks
        self.index = index
        self.index_dir = index_dir

    @classmethod
    def from_chunks(
        cls,
        chunks: list[RagChunk],
        embedding_model: EmbeddingModel,
        index_dir: Path,
    ) -> "FaissVectorStore":
        texts = [
            chunk.text
            for chunk in chunks
        ]

        embeddings = embedding_model.embed_texts(texts)

        if embeddings.size == 0:
            dimension = embedding_model.dimension
            index = faiss.IndexFlatIP(dimension)
        else:
            embeddings = embeddings.astype(np.float32)
            dimension = int(embeddings.shape[1])
            index = faiss.IndexFlatIP(dimension)
            index.add(embeddings)

        return cls(
            chunks=chunks,
            index=index,
            index_dir=index_dir,
        )

    @classmethod
    def load(cls, index_dir: Path) -> "FaissVectorStore":
        index_path = index_dir / cls.INDEX_FILENAME
        chunks_path = index_dir / cls.CHUNKS_FILENAME

        if not index_path.exists():
            raise FileNotFoundError(f"FAISS index not found: {index_path}")

        if not chunks_path.exists():
            raise FileNotFoundError(f"RAG chunks metadata not found: {chunks_path}")

        index = faiss.read_index(str(index_path))

        raw_chunks = json.loads(
            chunks_path.read_text(encoding="utf-8"),
        )

        chunks = [
            RagChunk.model_validate(item)
            for item in raw_chunks
        ]

        return cls(
            chunks=chunks,
            index=index,
            index_dir=index_dir,
        )

    def save(self) -> None:
        self.index_dir.mkdir(parents=True, exist_ok=True)

        index_path = self.index_dir / self.INDEX_FILENAME
        chunks_path = self.index_dir / self.CHUNKS_FILENAME

        faiss.write_index(
            self.index,
            str(index_path),
        )

        chunks_payload = [
            chunk.model_dump(mode="json")
            for chunk in self.chunks
        ]

        chunks_path.write_text(
            json.dumps(
                chunks_payload,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def search(
        self,
        query: str,
        embedding_model: EmbeddingModel,
        top_k: int = 3,
    ) -> list[RagSearchResult]:
        if not self.chunks:
            return []

        if self.index.ntotal == 0:
            return []

        query_embedding = embedding_model.embed_text(query)

        if np.linalg.norm(query_embedding) == 0:
            return []

        query_embedding = query_embedding.reshape(1, -1).astype(np.float32)

        scores, indices = self.index.search(
            query_embedding,
            top_k,
        )

        results: list[RagSearchResult] = []

        for score, index in zip(scores[0], indices[0], strict=False):
            if index < 0:
                continue

            if float(score) <= 0:
                continue

            chunk = self.chunks[int(index)]

            results.append(
                RagSearchResult(
                    chunk_id=chunk.chunk_id,
                    source_id=chunk.source_id,
                    title=chunk.title,
                    text=chunk.text,
                    score=round(float(score), 4),
                    metadata={
                        **chunk.metadata,
                        "retriever": "FaissVectorStore",
                    },
                )
            )

        return results

    @classmethod
    def index_exists(cls, index_dir: Path) -> bool:
        return (
            (index_dir / cls.INDEX_FILENAME).exists()
            and (index_dir / cls.CHUNKS_FILENAME).exists()
        )
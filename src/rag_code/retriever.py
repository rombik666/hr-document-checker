from pathlib import Path

from rag_code.embedder import SentenceTransformerEmbedder
from rag_code.vector_store import FaissVectorStore

class FaissRetriever:
    def __init__(self, embedding_model_name: str, index_path: Path, metadata_path: Path, top_k: int = 5,) -> None:
        self.embedding_model_name = embedding_model_name
        self.index_path = index_path
        self.metadata_path = metadata_path
        self.top_k = top_k

        self.embedder = SentenceTransformerEmbedder(embedding_model_name)
        self.vector_store = FaissVectorStore.load(
            index_path=index_path,
            metadata_path=metadata_path,
        )

    def retrieve(self, query: str, top_k: int | None = None) -> list[dict]:
        query = query.strip()

        if not query:
            raise ValueError("query must not be empty")
        
        effective_top_k = top_k if top_k is not None else self.top_k

        query_embedding = self.embedder.encode_query(query)
        results = self.vector_store.search(
            query_embeddings=query_embedding,
            top_k=effective_top_k,
        )

        for rank, item in enumerate(results, start = 1):
            item["rank"] = rank
            item["query"] = query

        return results
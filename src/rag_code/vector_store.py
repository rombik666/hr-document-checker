import json
import numpy as np

from pathlib import Path
import faiss

class FaissVectorStore:
    def __init__(self, dimension: int) -> None:
        self.dimension = dimension
        self.index = faiss.IndexFlatIP(dimension)
        self.metadata: list[dict] = []

    def add(self, embeddings: np.ndarray, metadata: list[dict]) -> None:
        if embeddings.ndim != 2:
            raise ValueError("embeddings must be a 2D array")
            
        if embeddings.shape[1] != self.dimension:
            raise ValueError(f"embedding dimension mismatch: expected {self.dimensio}, got {embeddings.shape[1]}")
        
        if embeddings.shape[0] != len(metadata):
            raise ValueError("number of embeddings must match number of metadara records")

        self.index.add(embeddings.astype("float32"))
        self.metadata.extend(metadata)

    def search(self, query_embeddings: np.ndarray, top_k: int = 5) -> list[dict]:
        if (query_embeddings.ndim != 2) or (query_embeddings.shape[0] != 1):
            raise ValueError("query_embedding must be have shape (1, dimension)")

        scores, indices = self.index.search(query_embeddings.astype("float32"), top_k)
        results: list[dict] = []
        for score, index_id in zip(scores[0], indices[0]):
            if index_id == -1:
                continue

            item = self.metadata[index_id].copy()
            item["score"] = float(score)
            item["faiss_index"] = int(index_id)
            results.append(item)

        return results
    
    def save(self, index_path: Path, metadata_path: Path) -> None:
        index_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path.parent.mkdir(parents=True, exist_ok=True)

        faiss.write_index(self.index, str(index_path))

        with metadata_path.open("w", encoding="utf-8") as file:
            json.dump(self.metadata, file, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, index_path: Path, metadata_path: Path) -> "FaissVectorStore":
        index = faiss.read_index(str(index_path))

        with metadata_path.open("r", encoding="utf-8") as file:
            metadata = json.load(file)

        vector_store = cls(dimension=index.d)
        vector_store.index = index
        vector_store.metadata = metadata
        return vector_store
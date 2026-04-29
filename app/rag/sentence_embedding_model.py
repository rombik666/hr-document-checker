from typing import Any

import numpy as np

from app.rag.embedding_model import EmbeddingModel


class SentenceTransformerEmbeddingModel:

    def __init__(
        self,
        model_name: str,
        dimension: int = 384,
    ) -> None:
        self.model_name = model_name
        self.dimension = dimension
        self._model = self._load_model(model_name)

    @staticmethod
    def _load_model(model_name: str) -> Any:
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer(model_name)

    def embed_text(self, text: str) -> np.ndarray:
        vectors = self.embed_texts([text])

        if vectors.shape[0] == 0:
            return np.zeros(self.dimension, dtype=np.float32)

        return vectors[0]

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, self.dimension), dtype=np.float32)

        embeddings = self._model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        embeddings = embeddings.astype(np.float32)

        if embeddings.ndim == 1:
            embeddings = embeddings.reshape(1, -1)

        self.dimension = int(embeddings.shape[1])

        return embeddings


def ensure_embedding_model_protocol(
    model: SentenceTransformerEmbeddingModel,
) -> EmbeddingModel:

    return model
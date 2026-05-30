from functools import lru_cache

from app.core.config import settings
from app.core.logging import get_logger
from app.rag.embedding_model import EmbeddingModel, HashingEmbeddingModel
from app.rag.sentence_embedding_model import SentenceTransformerEmbeddingModel


logger = get_logger(__name__)


def create_embedding_model() -> EmbeddingModel:
    backend = settings.rag_embedding_backend.lower().strip()

    return _create_embedding_model_cached(
        backend=backend,
        model_name=settings.rag_embedding_model_name,
        dimension=settings.rag_embedding_dimension,
        allow_fallback=settings.rag_allow_embedding_fallback,
    )


@lru_cache(maxsize=4)
def _create_embedding_model_cached(
    backend: str,
    model_name: str,
    dimension: int,
    allow_fallback: bool,
) -> EmbeddingModel:
    if backend == "sentence_transformer":
        try:
            logger.info(
                "loading_sentence_transformer model=%s",
                model_name,
            )

            return SentenceTransformerEmbeddingModel(
                model_name=model_name,
                dimension=dimension,
            )

        except Exception:
            if not allow_fallback:
                raise

            logger.exception(
                "sentence_transformer_loading_failed fallback=hashing"
            )

            return HashingEmbeddingModel(
                dimension=dimension,
            )

    return HashingEmbeddingModel(
        dimension=dimension,
    )


def clear_embedding_model_cache() -> None:
    _create_embedding_model_cached.cache_clear()
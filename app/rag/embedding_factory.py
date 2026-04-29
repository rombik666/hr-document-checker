from app.core.config import settings
from app.core.logging import get_logger
from app.rag.embedding_model import EmbeddingModel, HashingEmbeddingModel
from app.rag.sentence_embedding_model import SentenceTransformerEmbeddingModel


logger = get_logger(__name__)


def create_embedding_model() -> EmbeddingModel:

    backend = settings.rag_embedding_backend.lower().strip()

    if backend == "sentence_transformer":
        try:
            logger.info(
                "loading_sentence_transformer model=%s",
                settings.rag_embedding_model_name,
            )

            return SentenceTransformerEmbeddingModel(
                model_name=settings.rag_embedding_model_name,
                dimension=settings.rag_embedding_dimension,
            )

        except Exception:
            if not settings.rag_allow_embedding_fallback:
                raise

            logger.exception(
                "sentence_transformer_loading_failed fallback=hashing"
            )

            return HashingEmbeddingModel(
                dimension=settings.rag_embedding_dimension,
            )

    return HashingEmbeddingModel(
        dimension=settings.rag_embedding_dimension,
    )
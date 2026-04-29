import numpy as np

from app.rag.embedding_model import HashingEmbeddingModel


def test_hashing_embedding_model_returns_vector() -> None:
    model = HashingEmbeddingModel(dimension=128)

    vector = model.embed_text("Python FastAPI PostgreSQL Docker")

    assert vector.shape == (128,)
    assert vector.dtype == np.float32
    assert np.linalg.norm(vector) > 0


def test_hashing_embedding_model_is_deterministic() -> None:
    model = HashingEmbeddingModel(dimension=128)

    first = model.embed_text("Python FastAPI")
    second = model.embed_text("Python FastAPI")

    assert np.allclose(first, second)


def test_hashing_embedding_model_returns_empty_vector_for_empty_text() -> None:
    model = HashingEmbeddingModel(dimension=128)

    vector = model.embed_text("")

    assert vector.shape == (128,)
    assert np.linalg.norm(vector) == 0
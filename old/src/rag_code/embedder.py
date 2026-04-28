import numpy as np
from sentence_transformers import SentenceTransformer

class SentenceTransformerEmbedder:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)

    def encode_texts(self, texts: list[str], batch_size: int = 32, normalize_embeddings: bool = True) -> np.ndarray:
        embeddings = self.model.encode(
            texts,
            batch_size = batch_size,
            show_progress_bar = True,
            convert_to_numpy = True,
            normalize_embeddings = normalize_embeddings,
        )
        return embeddings.astype("float32")
    
    def encode_query(self, query: str) -> np.ndarray:
        return self.encode_texts([query], batch_size = 1)
import hashlib
import re
from typing import Protocol

import numpy as np


TOKEN_PATTERN = re.compile(r"[a-zA-Zа-яА-ЯёЁ0-9+#.-]+")


class EmbeddingModel(Protocol):

    dimension: int

    def embed_text(self, text: str) -> np.ndarray:
        ...

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        ...


class HashingEmbeddingModel:

    def __init__(self, dimension: int = 384) -> None:
        self.dimension = dimension

    def embed_text(self, text: str) -> np.ndarray:
        vector = np.zeros(self.dimension, dtype=np.float32)

        tokens = self._tokenize(text)

        if not tokens:
            return vector

        for token in tokens:
            digest = hashlib.md5(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], byteorder="little") % self.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0

            vector[index] += sign

        norm = np.linalg.norm(vector)

        if norm > 0:
            vector = vector / norm

        return vector.astype(np.float32)

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, self.dimension), dtype=np.float32)

        vectors = [
            self.embed_text(text)
            for text in texts
        ]

        return np.vstack(vectors).astype(np.float32)

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return [
            token.lower()
            for token in TOKEN_PATTERN.findall(text)
            if len(token.strip()) > 1
        ]
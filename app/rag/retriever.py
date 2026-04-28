import math
import re
from collections import Counter

from app.schemas.rag import RagChunk, RagSearchResult


TOKEN_PATTERN = re.compile(r"[a-zA-Zа-яА-ЯёЁ0-9+#.-]+")


class SimpleRagRetriever:

    def search(
        self,
        query: str,
        chunks: list[RagChunk],
        top_k: int = 3,
    ) -> list[RagSearchResult]:
        query_tokens = self._tokenize(query)

        if not query_tokens or not chunks:
            return []

        query_vector = Counter(query_tokens)

        scored_results: list[RagSearchResult] = []

        for chunk in chunks:
            chunk_tokens = self._tokenize(chunk.text)

            if not chunk_tokens:
                continue

            chunk_vector = Counter(chunk_tokens)
            score = self._cosine_similarity(query_vector, chunk_vector)

            if score <= 0:
                continue

            scored_results.append(
                RagSearchResult(
                    chunk_id=chunk.chunk_id,
                    source_id=chunk.source_id,
                    title=chunk.title,
                    text=chunk.text,
                    score=round(score, 4),
                    metadata=chunk.metadata,
                )
            )

        scored_results.sort(key=lambda result: result.score, reverse=True)

        return scored_results[:top_k]

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return [
            token.lower()
            for token in TOKEN_PATTERN.findall(text)
            if len(token.strip()) > 1
        ]

    @staticmethod
    def _cosine_similarity(
        left: Counter[str],
        right: Counter[str],
    ) -> float:
        common_tokens = set(left) & set(right)

        numerator = sum(left[token] * right[token] for token in common_tokens)

        left_norm = math.sqrt(sum(value * value for value in left.values()))
        right_norm = math.sqrt(sum(value * value for value in right.values()))

        if left_norm == 0 or right_norm == 0:
            return 0.0

        return numerator / (left_norm * right_norm)
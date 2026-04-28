from uuid import uuid4

from app.schemas.rag import RagChunk, RagSource


class TextChunker:

    def __init__(
        self,
        chunk_size_chars: int = 800,
        overlap_chars: int = 120,
    ) -> None:
        self.chunk_size_chars = chunk_size_chars
        self.overlap_chars = overlap_chars

    def chunk_sources(self, sources: list[RagSource]) -> list[RagChunk]:
        chunks: list[RagChunk] = []

        for source in sources:
            source_chunks = self.chunk_text(
                text=source.content,
                source_id=source.source_id,
                title=source.title,
            )
            chunks.extend(source_chunks)

        return chunks

    def chunk_text(
        self,
        text: str,
        source_id: str,
        title: str,
    ) -> list[RagChunk]:
        normalized_text = text.strip()

        if not normalized_text:
            return []

        chunks: list[RagChunk] = []

        start = 0
        position = 0

        while start < len(normalized_text):
            end = start + self.chunk_size_chars
            chunk_text = normalized_text[start:end].strip()

            if chunk_text:
                chunks.append(
                    RagChunk(
                        chunk_id=str(uuid4()),
                        source_id=source_id,
                        title=title,
                        text=chunk_text,
                        position=position,
                        metadata={
                            "start_char": start,
                            "end_char": min(end, len(normalized_text)),
                        },
                    )
                )

            if end >= len(normalized_text):
                break

            start = max(0, end - self.overlap_chars)
            position += 1

        return chunks
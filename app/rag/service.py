from pathlib import Path

from app.core.config import settings
from app.rag.chunker import TextChunker
from app.rag.knowledge_loader import KnowledgeLoader
from app.rag.retriever import SimpleRagRetriever
from app.schemas.rag import RagContext, RagSearchRequest


class RagService:

    def __init__(
        self,
        knowledge_base_dir: Path | None = None,
    ) -> None:
        self.knowledge_base_dir = knowledge_base_dir or settings.knowledge_base_dir
        self.loader = KnowledgeLoader()
        self.chunker = TextChunker(
            chunk_size_chars=settings.rag_chunk_size_chars,
            overlap_chars=settings.rag_chunk_overlap_chars,
        )
        self.retriever = SimpleRagRetriever()

    def search(self, request: RagSearchRequest) -> RagContext:
        sources = self.loader.load_sources(self.knowledge_base_dir)
        chunks = self.chunker.chunk_sources(sources)

        results = self.retriever.search(
            query=request.query,
            chunks=chunks,
            top_k=request.top_k,
        )

        return RagContext(
            query=request.query,
            results=results,
        )
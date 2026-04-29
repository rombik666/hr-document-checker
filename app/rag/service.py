from pathlib import Path

from app.core.config import settings
from app.rag.chunker import TextChunker
from app.rag.embedding_model import HashingEmbeddingModel
from app.rag.knowledge_loader import KnowledgeLoader
from app.rag.retriever import SimpleRagRetriever
from app.rag.vector_store import InMemoryVectorStore
from app.schemas.rag import RagContext, RagSearchRequest, RagStatus


class RagService:

    def __init__(
        self,
        knowledge_base_dir: Path | None = None,
        use_vector_search: bool | None = None,
    ) -> None:
        self.knowledge_base_dir = knowledge_base_dir or settings.knowledge_base_dir

        self.use_vector_search = (
            settings.rag_use_vector_search
            if use_vector_search is None
            else use_vector_search
        )

        self.loader = KnowledgeLoader()
        self.chunker = TextChunker(
            chunk_size_chars=settings.rag_chunk_size_chars,
            overlap_chars=settings.rag_chunk_overlap_chars,
        )
        self.simple_retriever = SimpleRagRetriever()
        self.embedding_model = HashingEmbeddingModel(
            dimension=settings.rag_embedding_dimension,
        )

    def search(self, request: RagSearchRequest) -> RagContext:
        sources = self.loader.load_sources(self.knowledge_base_dir)
        chunks = self.chunker.chunk_sources(sources)

        if self.use_vector_search:
            vector_store = InMemoryVectorStore.from_chunks(
                chunks=chunks,
                embedding_model=self.embedding_model,
            )

            results = vector_store.search(
                query=request.query,
                embedding_model=self.embedding_model,
                top_k=request.top_k,
            )

        else:
            results = self.simple_retriever.search(
                query=request.query,
                chunks=chunks,
                top_k=request.top_k,
            )

        return RagContext(
            query=request.query,
            results=results,
        )

    def get_status(self) -> RagStatus:
        sources = self.loader.load_sources(self.knowledge_base_dir)
        chunks = self.chunker.chunk_sources(sources)

        retriever_type = (
            "vector"
            if self.use_vector_search
            else "simple"
        )

        return RagStatus(
            knowledge_base_dir=str(self.knowledge_base_dir),
            sources_count=len(sources),
            chunks_count=len(chunks),
            retriever_type=retriever_type,
            embedding_dimension=(
                self.embedding_model.dimension
                if self.use_vector_search
                else None
            ),
        )
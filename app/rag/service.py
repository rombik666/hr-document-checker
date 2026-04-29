from pathlib import Path

from app.core.config import settings
from app.core.logging import get_logger
from app.rag.chunker import TextChunker
from app.rag.embedding_factory import create_embedding_model
from app.rag.faiss_store import FaissVectorStore
from app.rag.knowledge_loader import KnowledgeLoader
from app.rag.retriever import SimpleRagRetriever
from app.rag.vector_store import InMemoryVectorStore
from app.schemas.rag import RagContext, RagSearchRequest, RagStatus


logger = get_logger(__name__)


class RagService:

    def __init__(
    self,
    knowledge_base_dir: Path | None = None,
    index_dir: Path | None = None,
    use_vector_search: bool | None = None,
    ) -> None:
        self.knowledge_base_dir = knowledge_base_dir or settings.knowledge_base_dir

        if use_vector_search is False:
            self.retriever_type = "simple"
        elif use_vector_search is True:
            self.retriever_type = settings.rag_retriever_type
        else:
            self.retriever_type = settings.rag_retriever_type

        if index_dir is not None:
            self.index_dir = index_dir
        elif knowledge_base_dir is not None:
            self.index_dir = self.knowledge_base_dir.parent / "index"
        else:
            self.index_dir = settings.rag_index_dir

        self.loader = KnowledgeLoader()
        self.chunker = TextChunker(
            chunk_size_chars=settings.rag_chunk_size_chars,
            overlap_chars=settings.rag_chunk_overlap_chars,
        )
        self.simple_retriever = SimpleRagRetriever()
        self.embedding_model = create_embedding_model()

    def search(self, request: RagSearchRequest) -> RagContext:
        retriever = self.retriever_type.lower().strip()

        if retriever == "faiss":
            results = self._search_faiss(request)

        elif retriever == "vector":
            results = self._search_in_memory_vector(request)

        else:
            results = self._search_simple(request)

        return RagContext(
            query=request.query,
            results=results,
        )

    def _search_faiss(self, request: RagSearchRequest):
        if not FaissVectorStore.index_exists(self.index_dir):
            logger.info(
                "faiss_index_missing building_index index_dir=%s",
                self.index_dir,
            )
            self._build_faiss_index()

        vector_store = FaissVectorStore.load(self.index_dir)

        return vector_store.search(
            query=request.query,
            embedding_model=self.embedding_model,
            top_k=request.top_k,
        )

    def _build_faiss_index(self) -> None:
        sources = self.loader.load_sources(self.knowledge_base_dir)
        chunks = self.chunker.chunk_sources(sources)

        vector_store = FaissVectorStore.from_chunks(
            chunks=chunks,
            embedding_model=self.embedding_model,
            index_dir=self.index_dir,
        )

        vector_store.save()

    def _search_in_memory_vector(self, request: RagSearchRequest):
        sources = self.loader.load_sources(self.knowledge_base_dir)
        chunks = self.chunker.chunk_sources(sources)

        vector_store = InMemoryVectorStore.from_chunks(
            chunks=chunks,
            embedding_model=self.embedding_model,
        )

        return vector_store.search(
            query=request.query,
            embedding_model=self.embedding_model,
            top_k=request.top_k,
        )

    def _search_simple(self, request: RagSearchRequest):
        sources = self.loader.load_sources(self.knowledge_base_dir)
        chunks = self.chunker.chunk_sources(sources)

        return self.simple_retriever.search(
            query=request.query,
            chunks=chunks,
            top_k=request.top_k,
        )

    def get_status(self) -> RagStatus:
        sources = self.loader.load_sources(self.knowledge_base_dir)
        chunks = self.chunker.chunk_sources(sources)

        retriever = self.retriever_type.lower().strip()
        index_exists = FaissVectorStore.index_exists(self.index_dir)

        return RagStatus(
            knowledge_base_dir=str(self.knowledge_base_dir),
            sources_count=len(sources),
            chunks_count=len(chunks),
            retriever_type=retriever,
            embedding_dimension=self.embedding_model.dimension,
            embedding_backend=settings.rag_embedding_backend,
            embedding_model_name=(
                settings.rag_embedding_model_name
                if settings.rag_embedding_backend == "sentence_transformer"
                else "hashing"
            ),
            index_dir=str(self.index_dir),
            index_exists=index_exists,
        )
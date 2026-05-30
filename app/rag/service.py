from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.rag.chunker import TextChunker
from app.rag.embedding_factory import create_embedding_model
from app.rag.embedding_model import EmbeddingModel
from app.rag.faiss_store import FaissVectorStore
from app.rag.knowledge_loader import KnowledgeLoader
from app.rag.retriever import SimpleRagRetriever
from app.rag.vector_store import InMemoryVectorStore
from app.schemas.rag import RagContext, RagSearchRequest, RagStatus
from app.services.rag_source_service import RagSourceService


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

        # Важно: не self.embedding_model.
        # embedding_model ниже является @property без setter.
        self._embedding_model: EmbeddingModel | None = None

    @property
    def embedding_model(self) -> EmbeddingModel:
        if self._embedding_model is None:
            self._embedding_model = create_embedding_model()

        return self._embedding_model

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

    def search_user_sources(
        self,
        request: RagSearchRequest,
        db: Session,
        user_id: str,
        user_role: str,
    ) -> RagContext:
        source_service = RagSourceService(db)

        sources = source_service.load_active_rag_sources_for_user(
            user_id=user_id,
            user_role=user_role,
        )

        if not sources:
            return RagContext(
                query=request.query,
                results=[],
            )

        chunks = self.chunker.chunk_sources(sources)

        if not chunks:
            return RagContext(
                query=request.query,
                results=[],
            )

        retriever = self.retriever_type.lower().strip()

        if retriever == "vector":
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

    def get_user_sources_status(
        self,
        db: Session,
        user_id: str,
        user_role: str,
    ) -> RagStatus:
        source_service = RagSourceService(db)

        all_sources = source_service.list_sources_for_user(
            user_id=user_id,
            user_role=user_role,
            include_inactive=True,
            limit=1000,
        )

        active_sources = [
            source
            for source in all_sources
            if source.is_active
        ]

        rag_sources = [
            source_service.to_rag_source(source)
            for source in active_sources
        ]

        chunks = self.chunker.chunk_sources(rag_sources)

        embedding_model_name = (
            settings.rag_embedding_model_name
            if settings.rag_embedding_backend == "sentence_transformer"
            else "hashing"
        )

        return RagStatus(
            mode="db_sources",
            source_backend="database",
            user_scope="all" if user_role == "admin" else "own",
            knowledge_base_dir=None,
            sources_count=len(all_sources),
            active_sources_count=len(active_sources),
            inactive_sources_count=len(all_sources) - len(active_sources),
            chunks_count=len(chunks),
            retriever_type=self.retriever_type.lower().strip(),
            embedding_dimension=settings.rag_embedding_dimension,
            embedding_backend=settings.rag_embedding_backend,
            embedding_model_name=embedding_model_name,
            index_dir=None,
            index_exists=False,
            reindex_required=False,
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
            embedding_dimension=settings.rag_embedding_dimension,
            embedding_backend=settings.rag_embedding_backend,
            embedding_model_name=(
                settings.rag_embedding_model_name
                if settings.rag_embedding_backend == "sentence_transformer"
                else "hashing"
            ),
            index_dir=str(self.index_dir),
            index_exists=index_exists,
            reindex_required=not index_exists and retriever == "faiss",
        )
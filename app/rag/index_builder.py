from pathlib import Path

from app.core.config import settings
from app.core.logging import get_logger
from app.rag.chunker import TextChunker
from app.rag.embedding_factory import create_embedding_model
from app.rag.faiss_store import FaissVectorStore
from app.rag.knowledge_loader import KnowledgeLoader


logger = get_logger(__name__)


class RagIndexBuilder:

    def __init__(
        self,
        knowledge_base_dir: Path | None = None,
        index_dir: Path | None = None,
    ) -> None:
        self.knowledge_base_dir = knowledge_base_dir or settings.knowledge_base_dir
        self.index_dir = index_dir or settings.rag_index_dir

        self.loader = KnowledgeLoader()
        self.chunker = TextChunker(
            chunk_size_chars=settings.rag_chunk_size_chars,
            overlap_chars=settings.rag_chunk_overlap_chars,
        )

    def build(self) -> dict:
        sources = self.loader.load_sources(self.knowledge_base_dir)
        chunks = self.chunker.chunk_sources(sources)

        embedding_model = create_embedding_model()

        vector_store = FaissVectorStore.from_chunks(
            chunks=chunks,
            embedding_model=embedding_model,
            index_dir=self.index_dir,
        )

        vector_store.save()

        logger.info(
            "rag_faiss_index_built sources=%s chunks=%s index_dir=%s embedding_dimension=%s",
            len(sources),
            len(chunks),
            self.index_dir,
            embedding_model.dimension,
        )

        return {
            "knowledge_base_dir": str(self.knowledge_base_dir),
            "index_dir": str(self.index_dir),
            "sources_count": len(sources),
            "chunks_count": len(chunks),
            "embedding_dimension": embedding_model.dimension,
            "index_path": str(self.index_dir / FaissVectorStore.INDEX_FILENAME),
            "chunks_path": str(self.index_dir / FaissVectorStore.CHUNKS_FILENAME),
        }
import json
import re
from collections.abc import Iterable
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import RagIndexORM, RagIndexStatus, RagSourceORM
from app.rag.chunker import TextChunker
from app.rag.embedding_factory import create_embedding_model
from app.rag.embedding_model import EmbeddingModel
from app.rag.faiss_store import FaissVectorStore
from app.schemas.rag import RagContext, RagSearchRequest, RagSource


class RagIndexNotReadyError(Exception):
    """
    Ошибка состояния персонального RAG-индекса.

    Используется, когда пользователь пытается искать по RAG,
    но его FAISS-индекс отсутствует, устарел, строится или сломан.
    """

    def __init__(
        self,
        owner_user_id: str,
        status: str,
        reindex_required: bool,
        message: str,
        sources_count: int = 0,
        chunks_count: int = 0,
    ) -> None:
        super().__init__(message)

        self.owner_user_id = owner_user_id
        self.status = status
        self.reindex_required = reindex_required
        self.message = message
        self.sources_count = sources_count
        self.chunks_count = chunks_count

    def to_detail(self) -> dict:
        return {
            "error": "rag_reindex_required",
            "message": self.message,
            "owner_user_id": self.owner_user_id,
            "index_status": self.status,
            "reindex_required": self.reindex_required,
            "sources_count": self.sources_count,
            "chunks_count": self.chunks_count,
            "reindex_endpoint": "/api/v1/rag/reindex",
        }


class RagIndexService:
    """
    Сервис управления персональными FAISS-индексами пользователей.

    rag_sources хранят исходные маскированные RAG-источники в PostgreSQL.
    rag_indexes хранит состояние и метаданные индекса.
    faiss.index и chunks.json хранятся в файловом persistent volume.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.chunker = TextChunker(
            chunk_size_chars=settings.rag_chunk_size_chars,
            overlap_chars=settings.rag_chunk_overlap_chars,
        )
        self._embedding_model: EmbeddingModel | None = None

    @property
    def embedding_model(self) -> EmbeddingModel:
        if self._embedding_model is None:
            self._embedding_model = create_embedding_model()

        return self._embedding_model

    def get_index(self, owner_user_id: str) -> RagIndexORM | None:
        stmt = select(RagIndexORM).where(
            RagIndexORM.owner_user_id == owner_user_id,
        )

        return self.db.execute(stmt).scalar_one_or_none()

    def get_or_create_index(self, owner_user_id: str) -> RagIndexORM:
        existing_index = self.get_index(owner_user_id)

        if existing_index is not None:
            return existing_index

        now = self._now()
        index_dir = self.get_user_index_dir(owner_user_id)
        index_path = index_dir / FaissVectorStore.INDEX_FILENAME
        chunks_path = index_dir / FaissVectorStore.CHUNKS_FILENAME

        rag_index = RagIndexORM(
            id=str(uuid4()),
            owner_user_id=owner_user_id,
            status=RagIndexStatus.MISSING.value,
            reindex_required=True,
            index_path=str(index_path),
            chunks_path=str(chunks_path),
            sources_hash=None,
            sources_count=0,
            chunks_count=0,
            embedding_backend=settings.rag_embedding_backend,
            embedding_model_name=self._get_embedding_model_name(),
            embedding_dimension=settings.rag_embedding_dimension,
            retriever_type="faiss",
            index_metadata={
                "storage_backend": "filesystem",
                "index_dir": str(index_dir),
                "index_filename": FaissVectorStore.INDEX_FILENAME,
                "chunks_filename": FaissVectorStore.CHUNKS_FILENAME,
            },
            error_message=None,
            last_reindexed_at=None,
            created_at=now,
            updated_at=now,
        )

        self.db.add(rag_index)
        self.db.commit()
        self.db.refresh(rag_index)

        return rag_index

    def mark_index_stale(self, owner_user_id: str) -> RagIndexORM:
        rag_index = self.get_or_create_index(owner_user_id)
        active_sources = self.list_active_sources(owner_user_id)

        rag_index.status = RagIndexStatus.STALE.value
        rag_index.reindex_required = True
        rag_index.sources_hash = self.calculate_sources_hash(active_sources)
        rag_index.sources_count = len(active_sources)
        rag_index.error_message = None
        rag_index.updated_at = self._now()

        self.db.commit()
        self.db.refresh(rag_index)

        return rag_index

    def mark_index_building(self, owner_user_id: str) -> RagIndexORM:
        rag_index = self.get_or_create_index(owner_user_id)

        rag_index.status = RagIndexStatus.BUILDING.value
        rag_index.reindex_required = True
        rag_index.error_message = None
        rag_index.updated_at = self._now()

        self.db.commit()
        self.db.refresh(rag_index)

        return rag_index

    def mark_index_ready(
        self,
        owner_user_id: str,
        sources_hash: str | None = None,
        sources_count: int | None = None,
        chunks_count: int = 0,
        index_path: str | Path | None = None,
        chunks_path: str | Path | None = None,
        index_metadata: dict | None = None,
        embedding_backend: str | None = None,
        embedding_model_name: str | None = None,
        embedding_dimension: int | None = None,
        retriever_type: str = "faiss",
    ) -> RagIndexORM:
        rag_index = self.get_or_create_index(owner_user_id)

        active_sources = self.list_active_sources(owner_user_id)
        current_sources_hash = sources_hash or self.calculate_sources_hash(active_sources)
        current_sources_count = sources_count if sources_count is not None else len(active_sources)

        default_index_dir = self.get_user_index_dir(owner_user_id)
        default_index_path = default_index_dir / FaissVectorStore.INDEX_FILENAME
        default_chunks_path = default_index_dir / FaissVectorStore.CHUNKS_FILENAME

        now = self._now()

        rag_index.status = RagIndexStatus.READY.value
        rag_index.reindex_required = False
        rag_index.index_path = str(index_path or default_index_path)
        rag_index.chunks_path = str(chunks_path or default_chunks_path)
        rag_index.sources_hash = current_sources_hash
        rag_index.sources_count = current_sources_count
        rag_index.chunks_count = chunks_count
        rag_index.embedding_backend = embedding_backend or settings.rag_embedding_backend
        rag_index.embedding_model_name = embedding_model_name or self._get_embedding_model_name()
        rag_index.embedding_dimension = embedding_dimension or settings.rag_embedding_dimension
        rag_index.retriever_type = retriever_type
        rag_index.index_metadata = {
            **(rag_index.index_metadata or {}),
            **(index_metadata or {}),
            "storage_backend": "filesystem",
            "index_dir": str(default_index_dir),
        }
        rag_index.error_message = None
        rag_index.last_reindexed_at = now
        rag_index.updated_at = now

        self.db.commit()
        self.db.refresh(rag_index)

        return rag_index

    def mark_index_failed(
        self,
        owner_user_id: str,
        error_message: str,
    ) -> RagIndexORM:
        rag_index = self.get_or_create_index(owner_user_id)

        rag_index.status = RagIndexStatus.FAILED.value
        rag_index.reindex_required = True
        rag_index.error_message = error_message
        rag_index.updated_at = self._now()

        self.db.commit()
        self.db.refresh(rag_index)

        return rag_index

    def reindex_user_sources(self, owner_user_id: str) -> RagIndexORM:
        """
        Полностью перестраивает персональный FAISS-индекс пользователя.
        """

        self.mark_index_building(owner_user_id)

        try:
            active_sources = self.list_active_sources(owner_user_id)
            sources_hash = self.calculate_sources_hash(active_sources)

            rag_sources = [
                self._to_rag_source(source)
                for source in active_sources
            ]

            chunks = self.chunker.chunk_sources(rag_sources)

            index_dir = self.get_user_index_dir(owner_user_id)

            vector_store = FaissVectorStore.from_chunks(
                chunks=chunks,
                embedding_model=self.embedding_model,
                index_dir=index_dir,
            )
            vector_store.save()

            index_path, chunks_path = self.get_user_index_paths(owner_user_id)

            return self.mark_index_ready(
                owner_user_id=owner_user_id,
                sources_hash=sources_hash,
                sources_count=len(active_sources),
                chunks_count=len(chunks),
                index_path=index_path,
                chunks_path=chunks_path,
                embedding_backend=settings.rag_embedding_backend,
                embedding_model_name=self._get_embedding_model_name(),
                embedding_dimension=self.embedding_model.dimension,
                retriever_type="faiss",
                index_metadata={
                    "active_source_ids": [
                        source.id
                        for source in active_sources
                    ],
                    "chunk_size_chars": settings.rag_chunk_size_chars,
                    "chunk_overlap_chars": settings.rag_chunk_overlap_chars,
                    "index_filename": FaissVectorStore.INDEX_FILENAME,
                    "chunks_filename": FaissVectorStore.CHUNKS_FILENAME,
                },
            )

        except Exception as error:
            self.mark_index_failed(
                owner_user_id=owner_user_id,
                error_message=str(error),
            )
            raise

    def search_user_index(
        self,
        owner_user_id: str,
        request: RagSearchRequest,
    ) -> RagContext:
        """
        Выполняет поиск только по готовому персональному FAISS-индексу.

        Если индекс не готов, выбрасывает RagIndexNotReadyError.
        API-слой преобразует эту ошибку в HTTP 409.
        """

        rag_index = self.get_ready_index_or_raise(owner_user_id)

        index_dir = (
            Path(rag_index.index_path).parent
            if rag_index.index_path
            else self.get_user_index_dir(owner_user_id)
        )

        try:
            vector_store = FaissVectorStore.load(index_dir)

        except FileNotFoundError as error:
            rag_index = self.mark_index_stale(owner_user_id)
            raise RagIndexNotReadyError(
                owner_user_id=owner_user_id,
                status=rag_index.status,
                reindex_required=rag_index.reindex_required,
                message=(
                    "Personal RAG index files are missing. "
                    "Run POST /api/v1/rag/reindex before search."
                ),
                sources_count=rag_index.sources_count,
                chunks_count=rag_index.chunks_count,
            ) from error

        results = vector_store.search(
            query=request.query,
            embedding_model=self.embedding_model,
            top_k=request.top_k,
        )

        return RagContext(
            query=request.query,
            results=results,
        )

    def get_ready_index_or_raise(self, owner_user_id: str) -> RagIndexORM:
        """
        Возвращает готовый индекс или объяснимо сообщает,
        что нужна переиндексация.
        """

        rag_index = self.get_or_create_index(owner_user_id)

        active_sources = self.list_active_sources(owner_user_id)
        current_sources_hash = self.calculate_sources_hash(active_sources)

        if rag_index.sources_hash != current_sources_hash:
            rag_index = self.mark_index_stale(owner_user_id)
            raise self._not_ready_error(
                owner_user_id=owner_user_id,
                rag_index=rag_index,
                message=(
                    "Personal RAG index is stale because active sources changed. "
                    "Run POST /api/v1/rag/reindex before search."
                ),
            )

        if rag_index.status != RagIndexStatus.READY.value:
            raise self._not_ready_error(
                owner_user_id=owner_user_id,
                rag_index=rag_index,
                message=(
                    f"Personal RAG index is not ready: status={rag_index.status}. "
                    "Run POST /api/v1/rag/reindex before search."
                ),
            )

        if rag_index.reindex_required:
            raise self._not_ready_error(
                owner_user_id=owner_user_id,
                rag_index=rag_index,
                message=(
                    "Personal RAG index requires reindex. "
                    "Run POST /api/v1/rag/reindex before search."
                ),
            )

        if not rag_index.index_path or not rag_index.chunks_path:
            rag_index = self.mark_index_stale(owner_user_id)
            raise self._not_ready_error(
                owner_user_id=owner_user_id,
                rag_index=rag_index,
                message=(
                    "Personal RAG index metadata is incomplete. "
                    "Run POST /api/v1/rag/reindex before search."
                ),
            )

        index_path = Path(rag_index.index_path)
        chunks_path = Path(rag_index.chunks_path)

        if not index_path.exists() or not chunks_path.exists():
            rag_index = self.mark_index_stale(owner_user_id)
            raise self._not_ready_error(
                owner_user_id=owner_user_id,
                rag_index=rag_index,
                message=(
                    "Personal RAG index files are missing. "
                    "Run POST /api/v1/rag/reindex before search."
                ),
            )

        return rag_index

    def list_active_sources(self, owner_user_id: str) -> list[RagSourceORM]:
        stmt = (
            select(RagSourceORM)
            .where(RagSourceORM.owner_user_id == owner_user_id)
            .where(RagSourceORM.is_active.is_(True))
            .order_by(RagSourceORM.id)
        )

        return list(self.db.execute(stmt).scalars().all())

    def calculate_current_sources_hash(self, owner_user_id: str) -> str:
        active_sources = self.list_active_sources(owner_user_id)

        return self.calculate_sources_hash(active_sources)

    def calculate_sources_hash(self, sources: Iterable[RagSourceORM]) -> str:
        payload = [
            {
                "id": source.id,
                "content_hash": source.content_hash,
                "source_type": source.source_type,
                "source_format": source.source_format,
                "is_active": source.is_active,
                "updated_at": self._datetime_to_iso(source.updated_at),
            }
            for source in sorted(
                sources,
                key=lambda item: item.id,
            )
        ]

        serialized_payload = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

        return sha256(serialized_payload.encode("utf-8")).hexdigest()

    def needs_reindex(self, owner_user_id: str) -> bool:
        rag_index = self.get_index(owner_user_id)

        if rag_index is None:
            return True

        if rag_index.status != RagIndexStatus.READY.value:
            return True

        if rag_index.reindex_required:
            return True

        current_sources_hash = self.calculate_current_sources_hash(owner_user_id)

        if rag_index.sources_hash != current_sources_hash:
            return True

        if not rag_index.index_path or not rag_index.chunks_path:
            return True

        index_path = Path(rag_index.index_path)
        chunks_path = Path(rag_index.chunks_path)

        return not index_path.exists() or not chunks_path.exists()

    def get_user_index_dir(self, owner_user_id: str) -> Path:
        safe_owner_id = self._safe_path_part(owner_user_id)

        return settings.rag_index_dir / "users" / safe_owner_id

    def get_user_index_paths(self, owner_user_id: str) -> tuple[Path, Path]:
        index_dir = self.get_user_index_dir(owner_user_id)

        return (
            index_dir / FaissVectorStore.INDEX_FILENAME,
            index_dir / FaissVectorStore.CHUNKS_FILENAME,
        )

    def _not_ready_error(
        self,
        owner_user_id: str,
        rag_index: RagIndexORM,
        message: str,
    ) -> RagIndexNotReadyError:
        return RagIndexNotReadyError(
            owner_user_id=owner_user_id,
            status=rag_index.status,
            reindex_required=rag_index.reindex_required,
            message=message,
            sources_count=rag_index.sources_count,
            chunks_count=rag_index.chunks_count,
        )

    @staticmethod
    def _to_rag_source(source: RagSourceORM) -> RagSource:
        return RagSource(
            source_id=source.id,
            title=source.title,
            path=f"db://rag_sources/{source.id}",
            content=source.content,
        )

    @staticmethod
    def _safe_path_part(value: str) -> str:
        safe_value = re.sub(r"[^a-zA-Z0-9_.-]+", "_", value).strip("._")

        return safe_value or "unknown_user"

    @staticmethod
    def _datetime_to_iso(value: datetime | None) -> str | None:
        if value is None:
            return None

        return value.isoformat()

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _get_embedding_model_name() -> str:
        if settings.rag_embedding_backend == "sentence_transformer":
            return settings.rag_embedding_model_name

        return "hashing"
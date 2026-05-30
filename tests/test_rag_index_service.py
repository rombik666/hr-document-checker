from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db.models import Base, RagIndexStatus, RagSourceORM, UserORM
from app.rag.faiss_store import FaissVectorStore
from app.services.rag_index_service import RagIndexService


def make_test_db() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={
            "check_same_thread": False,
        },
    )

    Base.metadata.create_all(bind=engine)

    session_local = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )

    return session_local()


def create_user(db: Session, user_id: str = "hr-user-1") -> UserORM:
    user = UserORM(
        id=user_id,
        email=f"{user_id}@example.com",
        full_name=f"User {user_id}",
        role="hr",
        password_hash="test-password-hash",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def create_rag_source(
    db: Session,
    owner_user_id: str,
    source_id: str,
    content_hash: str,
    is_active: bool = True,
) -> RagSourceORM:
    now = datetime.now(timezone.utc)

    source = RagSourceORM(
        id=source_id,
        owner_user_id=owner_user_id,
        title=f"Source {source_id}",
        filename=f"{source_id}.txt",
        source_type="vacancy",
        source_format="txt",
        content=f"Python FastAPI PostgreSQL source {source_id}",
        content_hash=content_hash,
        file_size_bytes=128,
        is_active=is_active,
        source_metadata={
            "test": True,
        },
        created_at=now,
        updated_at=now,
    )

    db.add(source)
    db.commit()
    db.refresh(source)

    return source


def test_rag_index_service_creates_missing_index(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        settings,
        "rag_index_dir",
        tmp_path / "index",
    )

    db = make_test_db()

    try:
        create_user(db, "hr-user-1")

        service = RagIndexService(db)
        rag_index = service.get_or_create_index("hr-user-1")

        expected_index_dir = tmp_path / "index" / "users" / "hr-user-1"

        assert rag_index.id
        assert rag_index.owner_user_id == "hr-user-1"
        assert rag_index.status == RagIndexStatus.MISSING.value
        assert rag_index.reindex_required is True
        assert rag_index.index_path == str(expected_index_dir / FaissVectorStore.INDEX_FILENAME)
        assert rag_index.chunks_path == str(expected_index_dir / FaissVectorStore.CHUNKS_FILENAME)
        assert rag_index.sources_hash is None
        assert rag_index.sources_count == 0
        assert rag_index.chunks_count == 0
        assert rag_index.embedding_backend == settings.rag_embedding_backend
        assert rag_index.embedding_dimension == settings.rag_embedding_dimension
        assert rag_index.retriever_type == "faiss"

        same_index = service.get_or_create_index("hr-user-1")

        assert same_index.id == rag_index.id

    finally:
        db.close()


def test_rag_index_service_marks_index_stale_and_updates_sources_hash(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        settings,
        "rag_index_dir",
        tmp_path / "index",
    )

    db = make_test_db()

    try:
        create_user(db, "hr-user-1")

        create_rag_source(
            db=db,
            owner_user_id="hr-user-1",
            source_id="source-1",
            content_hash="a" * 64,
            is_active=True,
        )
        create_rag_source(
            db=db,
            owner_user_id="hr-user-1",
            source_id="source-2",
            content_hash="b" * 64,
            is_active=True,
        )
        create_rag_source(
            db=db,
            owner_user_id="hr-user-1",
            source_id="source-inactive",
            content_hash="c" * 64,
            is_active=False,
        )

        service = RagIndexService(db)
        rag_index = service.mark_index_stale("hr-user-1")

        assert rag_index.status == RagIndexStatus.STALE.value
        assert rag_index.reindex_required is True
        assert rag_index.sources_count == 2
        assert rag_index.sources_hash is not None
        assert len(rag_index.sources_hash) == 64
        assert rag_index.error_message is None

    finally:
        db.close()


def test_rag_index_service_hash_is_order_independent() -> None:
    db = make_test_db()

    try:
        create_user(db, "hr-user-1")

        source_1 = create_rag_source(
            db=db,
            owner_user_id="hr-user-1",
            source_id="source-1",
            content_hash="a" * 64,
        )
        source_2 = create_rag_source(
            db=db,
            owner_user_id="hr-user-1",
            source_id="source-2",
            content_hash="b" * 64,
        )

        service = RagIndexService(db)

        first_hash = service.calculate_sources_hash(
            [
                source_1,
                source_2,
            ]
        )
        second_hash = service.calculate_sources_hash(
            [
                source_2,
                source_1,
            ]
        )

        assert first_hash == second_hash
        assert len(first_hash) == 64

    finally:
        db.close()


def test_rag_index_service_marks_index_building_ready_and_failed(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        settings,
        "rag_index_dir",
        tmp_path / "index",
    )

    db = make_test_db()

    try:
        create_user(db, "hr-user-1")

        create_rag_source(
            db=db,
            owner_user_id="hr-user-1",
            source_id="source-1",
            content_hash="a" * 64,
        )

        service = RagIndexService(db)

        building_index = service.mark_index_building("hr-user-1")

        assert building_index.status == RagIndexStatus.BUILDING.value
        assert building_index.reindex_required is True

        index_path, chunks_path = service.get_user_index_paths("hr-user-1")
        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_path.write_bytes(b"test-faiss-index-placeholder")
        chunks_path.write_text("[]", encoding="utf-8")

        ready_index = service.mark_index_ready(
            owner_user_id="hr-user-1",
            chunks_count=5,
            index_metadata={
                "test_reindex": True,
            },
        )

        assert ready_index.status == RagIndexStatus.READY.value
        assert ready_index.reindex_required is False
        assert ready_index.sources_count == 1
        assert ready_index.chunks_count == 5
        assert ready_index.last_reindexed_at is not None
        assert ready_index.error_message is None
        assert ready_index.index_metadata["test_reindex"] is True

        assert service.needs_reindex("hr-user-1") is False

        failed_index = service.mark_index_failed(
            owner_user_id="hr-user-1",
            error_message="Test reindex failed.",
        )

        assert failed_index.status == RagIndexStatus.FAILED.value
        assert failed_index.reindex_required is True
        assert failed_index.error_message == "Test reindex failed."
        assert service.needs_reindex("hr-user-1") is True

    finally:
        db.close()
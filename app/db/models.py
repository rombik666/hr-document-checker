from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """
    Базовый класс для всех ORM-моделей.
    """

    pass


class UserRole(StrEnum):
    CANDIDATE = "candidate"
    HR = "hr"
    ADMIN = "admin"


class RagIndexStatus(StrEnum):
    """
    Состояние персонального FAISS-индекса пользователя.
    """

    MISSING = "missing"
    STALE = "stale"
    BUILDING = "building"
    READY = "ready"
    FAILED = "failed"


class UserORM(Base):
    """
    Таблица пользователей системы.
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    role: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )

    password_hash: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class DocumentORM(Base):
    """
    Таблица документов.

    Хранит только метаданные документа. Исходный текст документа
    в долговременной БД не сохраняется.
    """

    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)

    owner_user_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )

    filename: Mapped[str] = mapped_column(String(255), nullable=False)

    document_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_format: Mapped[str] = mapped_column(String(32), nullable=False)
    processing_status: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_mode: Mapped[str] = mapped_column(String(64), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    sections: Mapped[list["DocumentSectionORM"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )

    processing_sessions: Mapped[list["ProcessingSessionORM"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )

    reports: Mapped[list["ReportORM"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )


class DocumentSectionORM(Base):
    """
    Физическая таблица секций документа.

    Соответствует логической сущности DocumentSection из ER-модели.
    """

    __tablename__ = "document_sections"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)

    document_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    section_type: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    position_in_document: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    section_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    document: Mapped[DocumentORM] = relationship(back_populates="sections")


class ProcessingSessionORM(Base):
    """
    Сессия обработки документа.

    Нужна для сценария: один документ может проверяться несколько раз,
    в том числе с разными вакансиями.
    """

    __tablename__ = "processing_sessions"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)

    document_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    owner_user_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )

    status: Mapped[str] = mapped_column(String(64), nullable=False, default="completed")

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)

    session_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    document: Mapped[DocumentORM] = relationship(back_populates="processing_sessions")

    checks: Mapped[list["CheckORM"]] = relationship(
        back_populates="processing_session",
        cascade="all, delete-orphan",
    )

    reports: Mapped[list["ReportORM"]] = relationship(
        back_populates="processing_session",
    )


class CheckORM(Base):
    """
    Физическая таблица запусков проверок/агентов.
    """

    __tablename__ = "checks"

    id: Mapped[str] = mapped_column(String(160), primary_key=True)

    processing_session_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("processing_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    document_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    report_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    agent_name: Mapped[str] = mapped_column(String(128), nullable=False)
    check_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    model_or_ruleset_version: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        default="ruleset-1.0.0",
    )

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    processing_session: Mapped[ProcessingSessionORM] = relationship(back_populates="checks")

    issues: Mapped[list["IssueORM"]] = relationship(
        back_populates="check",
        cascade="all, delete-orphan",
    )


class IssueORM(Base):
    """
    Физическая таблица выявленных проблем.
    """

    __tablename__ = "issues"

    id: Mapped[str] = mapped_column(String(160), primary_key=True)

    check_id: Mapped[str] = mapped_column(
        String(160),
        ForeignKey("checks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    document_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    report_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    severity: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    issue_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_fragment: Mapped[str | None] = mapped_column(Text, nullable=True)

    source_agent: Mapped[str] = mapped_column(String(128), nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    issue_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    check: Mapped[CheckORM] = relationship(back_populates="issues")

    recommendation: Mapped["RecommendationORM | None"] = relationship(
        back_populates="issue",
        cascade="all, delete-orphan",
        uselist=False,
    )


class RecommendationORM(Base):
    """
    Физическая таблица рекомендаций по исправлению проблем.
    """

    __tablename__ = "recommendations"

    id: Mapped[str] = mapped_column(String(160), primary_key=True)

    issue_id: Mapped[str] = mapped_column(
        String(160),
        ForeignKey("issues.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    recommendation_text: Mapped[str] = mapped_column(Text, nullable=False)
    example_fix: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    issue: Mapped[IssueORM] = relationship(back_populates="recommendation")


class ReportORM(Base):
    """
    Таблица отчётов.

    report_json сохраняется для быстрого восстановления пользовательского отчёта,
    а checks/issues/recommendations хранятся отдельно для соответствия ER-модели.
    """

    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)

    owner_user_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )

    document_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    processing_session_id: Mapped[str | None] = mapped_column(
        String(128),
        ForeignKey("processing_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    summary_status: Mapped[str] = mapped_column(String(64), nullable=False)

    total_issues: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    critical_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    major_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    minor_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    summary: Mapped[str] = mapped_column(Text, nullable=False)
    report_json: Mapped[dict] = mapped_column(JSON, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    document: Mapped[DocumentORM] = relationship(back_populates="reports")

    processing_session: Mapped[ProcessingSessionORM | None] = relationship(
        back_populates="reports",
    )


class RagIndexORM(Base):
    """
    Метаданные персонального FAISS-индекса пользователя.

    Сам бинарный faiss.index и chunks.json не хранятся в PostgreSQL.
    В БД сохраняются только статус, пути, hash активных источников
    и технические параметры индекса.
    """

    __tablename__ = "rag_indexes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)

    owner_user_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=RagIndexStatus.MISSING.value,
        index=True,
    )

    reindex_required: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    index_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    chunks_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    sources_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )

    sources_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    chunks_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    embedding_backend: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="hashing",
    )

    embedding_model_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="hashing",
    )

    embedding_dimension: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=384,
    )

    retriever_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="faiss",
    )

    index_metadata: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    last_reindexed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class RagSourceORM(Base):
    """
    Таблица пользовательских RAG-источников.

    Хранит маскированное содержимое загруженных HR/admin документов,
    из которых затем строится персональный FAISS-индекс.
    """

    __tablename__ = "rag_sources"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)

    owner_user_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)

    source_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="other",
        index=True,
    )

    source_format: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )

    content: Mapped[str] = mapped_column(Text, nullable=False)

    content_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )

    file_size_bytes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    source_metadata: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
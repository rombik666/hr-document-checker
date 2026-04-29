from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from enum import StrEnum
from sqlalchemy import Boolean


class Base(DeclarativeBase):
    """
    Базовый класс для всех ORM-моделей.
    
    """

    pass

class UserRole(StrEnum):
    CANDIDATE = "candidate"
    HR = "hr"
    ADMIN = "admin"


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

    reports: Mapped[list["ReportORM"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )


class ReportORM(Base):
    """
    Таблица отчётов.

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
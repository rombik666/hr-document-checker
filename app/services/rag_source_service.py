from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.privacy import mask_text
from app.db.models import RagSourceORM
from app.parsers.parser_factory import ParserFactory
from app.schemas.rag import (
    RagSource,
    UserRagSourceDetails,
    UserRagSourceListItem,
)


class RagSourceService:
    """
    Сервис управления пользовательскими RAG-источниками.

    Используется для документов, которые HR/admin явно загружает
    в корпоративную RAG-базу знаний: вакансии, чек-листы,
    регламенты, требования к оформлению документов.
    """

    SUPPORTED_SUFFIXES = {
        ".docx",
        ".pdf",
        ".txt",
        ".md",
    }

    ALLOWED_SOURCE_TYPES = {
        "vacancy",
        "policy",
        "checklist",
        "requirements",
        "other",
    }

    MAX_SINGLE_FILE_SIZE_BYTES = 15 * 1024 * 1024
    MAX_USER_STORAGE_BYTES = 100 * 1024 * 1024

    def __init__(self, db: Session) -> None:
        self.db = db

    def create_source_from_file(
        self,
        file_path: Path,
        original_filename: str,
        owner_user_id: str,
        title: str | None = None,
        source_type: str = "other",
        file_size_bytes: int | None = None,
    ) -> RagSourceORM:
        suffix = self._validate_suffix(file_path)

        actual_file_size_bytes = (
            file_size_bytes
            if file_size_bytes is not None
            else file_path.stat().st_size
        )

        self._validate_single_file_size(actual_file_size_bytes)
        self._validate_user_storage_quota(
            owner_user_id=owner_user_id,
            new_file_size_bytes=actual_file_size_bytes,
        )

        normalized_source_type = self._normalize_source_type(source_type)

        extracted_content = self._extract_content(file_path)
        sanitized_content = mask_text(extracted_content).strip()

        if not sanitized_content:
            raise ValueError("RAG source content is empty.")

        safe_filename = mask_text(original_filename).strip() or "rag_source"
        safe_title = mask_text(title or Path(original_filename).stem).strip()

        if not safe_title:
            safe_title = "RAG source"

        now = datetime.now(timezone.utc)
        content_hash = self._calculate_hash(sanitized_content)

        source = RagSourceORM(
            id=str(uuid4()),
            owner_user_id=owner_user_id,
            title=safe_title,
            filename=safe_filename,
            source_type=normalized_source_type,
            source_format=suffix.lstrip("."),
            content=sanitized_content,
            content_hash=content_hash,
            file_size_bytes=actual_file_size_bytes,
            is_active=True,
            source_metadata={
                "original_suffix": suffix,
                "content_length": len(sanitized_content),
                "file_size_bytes": actual_file_size_bytes,
            },
            created_at=now,
            updated_at=now,
        )

        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)

        return source

    def list_sources_for_user(
        self,
        user_id: str,
        user_role: str,
        include_inactive: bool = False,
        limit: int = 100,
    ) -> list[RagSourceORM]:
        stmt = select(RagSourceORM)

        if user_role != "admin":
            stmt = stmt.where(RagSourceORM.owner_user_id == user_id)

        if not include_inactive:
            stmt = stmt.where(RagSourceORM.is_active.is_(True))

        stmt = (
            stmt
            .order_by(RagSourceORM.created_at.desc())
            .limit(limit)
        )

        return list(self.db.execute(stmt).scalars().all())

    def get_source_for_user(
        self,
        source_id: str,
        user_id: str,
        user_role: str,
    ) -> RagSourceORM | None:
        source = self.db.get(RagSourceORM, source_id)

        if source is None:
            return None

        if not self.user_can_access_source(
            source=source,
            user_id=user_id,
            user_role=user_role,
        ):
            return None

        return source

    def deactivate_source_for_user(
        self,
        source_id: str,
        user_id: str,
        user_role: str,
    ) -> bool:
        source = self.get_source_for_user(
            source_id=source_id,
            user_id=user_id,
            user_role=user_role,
        )

        if source is None:
            return False

        source.is_active = False
        source.updated_at = datetime.now(timezone.utc)

        self.db.commit()

        return True

    def load_active_rag_sources_for_user(
        self,
        user_id: str,
        user_role: str,
    ) -> list[RagSource]:
        sources = self.list_sources_for_user(
            user_id=user_id,
            user_role=user_role,
            include_inactive=False,
            limit=1000,
        )

        return [
            self.to_rag_source(source)
            for source in sources
        ]

    def get_active_storage_usage_bytes(self, owner_user_id: str) -> int:
        value = self.db.execute(
            select(func.coalesce(func.sum(RagSourceORM.file_size_bytes), 0))
            .where(RagSourceORM.owner_user_id == owner_user_id)
            .where(RagSourceORM.is_active.is_(True))
        ).scalar_one()

        return int(value or 0)

    @staticmethod
    def user_can_access_source(
        source: RagSourceORM,
        user_id: str,
        user_role: str,
    ) -> bool:
        if user_role == "admin":
            return True

        return source.owner_user_id == user_id

    @staticmethod
    def to_list_item(source: RagSourceORM) -> UserRagSourceListItem:
        return UserRagSourceListItem(
            source_id=source.id,
            title=source.title,
            filename=source.filename,
            source_type=source.source_type,
            source_format=source.source_format,
            content_length=len(source.content),
            file_size_bytes=source.file_size_bytes,
            is_active=source.is_active,
            created_at=source.created_at,
            updated_at=source.updated_at,
        )

    @staticmethod
    def to_details(source: RagSourceORM) -> UserRagSourceDetails:
        return UserRagSourceDetails(
            source_id=source.id,
            title=source.title,
            filename=source.filename,
            source_type=source.source_type,
            source_format=source.source_format,
            content=source.content,
            content_length=len(source.content),
            file_size_bytes=source.file_size_bytes,
            content_hash=source.content_hash,
            is_active=source.is_active,
            metadata=source.source_metadata,
            created_at=source.created_at,
            updated_at=source.updated_at,
        )

    @staticmethod
    def to_rag_source(source: RagSourceORM) -> RagSource:
        return RagSource(
            source_id=source.id,
            title=source.title,
            path=f"db://rag_sources/{source.id}",
            content=source.content,
        )

    @classmethod
    def _validate_suffix(cls, file_path: Path) -> str:
        suffix = file_path.suffix.lower()

        if suffix not in cls.SUPPORTED_SUFFIXES:
            raise ValueError(
                f"Unsupported RAG source format: {suffix}. "
                f"Supported formats: {', '.join(sorted(cls.SUPPORTED_SUFFIXES))}."
            )

        return suffix

    @classmethod
    def _normalize_source_type(cls, source_type: str) -> str:
        normalized = source_type.strip().lower() or "other"

        if normalized not in cls.ALLOWED_SOURCE_TYPES:
            raise ValueError(
                f"Unsupported RAG source type: {source_type}. "
                f"Supported types: {', '.join(sorted(cls.ALLOWED_SOURCE_TYPES))}."
            )

        return normalized

    @classmethod
    def _validate_single_file_size(cls, file_size_bytes: int) -> None:
        if file_size_bytes > cls.MAX_SINGLE_FILE_SIZE_BYTES:
            raise ValueError(
                "RAG source file is too large. "
                "Maximum allowed file size is 15 MB."
            )

    def _validate_user_storage_quota(
        self,
        owner_user_id: str,
        new_file_size_bytes: int,
    ) -> None:
        current_usage_bytes = self.get_active_storage_usage_bytes(owner_user_id)
        projected_usage_bytes = current_usage_bytes + new_file_size_bytes

        if projected_usage_bytes > self.MAX_USER_STORAGE_BYTES:
            raise ValueError(
                "RAG source storage quota exceeded. "
                "Maximum total active storage per HR user is 100 MB."
            )

    @staticmethod
    def _extract_content(file_path: Path) -> str:
        suffix = file_path.suffix.lower()

        if suffix in {".txt", ".md"}:
            return file_path.read_text(encoding="utf-8")

        parser = ParserFactory.get_parser(file_path)
        parsed_document = parser.parse(file_path)

        return parsed_document.raw_text

    @staticmethod
    def _calculate_hash(content: str) -> str:
        return sha256(content.encode("utf-8")).hexdigest()
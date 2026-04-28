from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import (
    DocumentType,
    EntityType,
    ProcessingStatus,
    SourceFormat,
    StorageMode,
)


class DocumentMetadata(BaseModel):
    """
    Метаданные документа.

    Это техническая информация о файле:
    id, имя файла, формат, статус обработки, режим хранения.
    """

    document_id: str
    document_type: DocumentType = DocumentType.UNKNOWN
    source_format: SourceFormat = SourceFormat.UNKNOWN
    filename: str
    upload_time: datetime
    processing_status: ProcessingStatus = ProcessingStatus.UPLOADED
    storage_mode: StorageMode = StorageMode.TEMPORARY
    hash: str | None = None
    warnings: list[str] = Field(default_factory=list)


class DocumentSection(BaseModel):
    """
    Секция документа.

    На этапе парсинга секцией может быть:
    - абзац DOCX;
    - таблица DOCX;
    - страница PDF.

    Позже мы научимся определять смысловые секции:
    contacts, experience, skills, education, projects.
    """

    section_id: str
    section_type: str
    title: str | None = None
    text: str
    position_in_document: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExtractedEntity(BaseModel):
    """
    Извлечённая сущность из документа.

    Например:
    - email;
    - телефон;
    - ссылка;
    - дата;
    - навык;
    - должность.
    """

    entity_id: str
    entity_type: EntityType
    value: str
    normalized_value: str | None = None
    source_section_id: str | None = None
    start_char: int | None = None
    end_char: int | None = None
    confidence_score: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ParsedDocument(BaseModel):
    """
    Результат парсинга документа.

    Это главный объект этапа 3.

    Его будут получать:
    - экстракторы сущностей;
    - формальные агенты;
    - семантические агенты;
    - агент-координатор.
    """

    metadata: DocumentMetadata
    raw_text: str
    sections: list[DocumentSection] = Field(default_factory=list)
    entities: list[ExtractedEntity] = Field(default_factory=list)


class DocumentUploadParams(BaseModel):
    """
    Параметры загрузки документа.

    Пока почти не используется, но позже пригодится для API:
    пользователь сможет выбрать тип документа и режим хранения.
    """

    document_type: DocumentType = DocumentType.UNKNOWN
    storage_mode: StorageMode = StorageMode.TEMPORARY
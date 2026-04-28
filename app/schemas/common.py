from enum import StrEnum


class DocumentType(StrEnum):
    """
    Тип документа.

    Пока парсер не определяет тип документа автоматически,
    поэтому по умолчанию используем UNKNOWN.
    Позже на этапе классификации документа будем определять:
    резюме, сопроводительное письмо, анкету, вакансию.
    """

    CV = "cv"
    COVER_LETTER = "cover_letter"
    CANDIDATE_FORM = "candidate_form"
    VACANCY = "vacancy"
    UNKNOWN = "unknown"


class SourceFormat(StrEnum):
    """
    Исходный формат загруженного файла.
    """

    DOCX = "docx"
    PDF = "pdf"
    TXT = "txt"
    UNKNOWN = "unknown"


class ProcessingStatus(StrEnum):
    """
    Статус обработки документа.
    """

    UPLOADED = "uploaded"
    PARSED = "parsed"
    FAILED = "failed"
    CHECKED = "checked"
    REPORT_GENERATED = "report_generated"


class StorageMode(StrEnum):
    """
    Режим хранения документа.

    TEMPORARY — документ временно сохраняется для обработки.
    NO_STORE — документ не должен сохраняться после обработки.
    METADATA_ONLY — сохраняются только метаданные и отчёт.
    """

    TEMPORARY = "temporary"
    NO_STORE = "no_store"
    METADATA_ONLY = "metadata_only"


class EntityType(StrEnum):
    """
    Типы сущностей, которые позже будем извлекать из документа.
    """

    EMAIL = "email"
    PHONE = "phone"
    URL = "url"
    DATE = "date"
    SKILL = "skill"
    POSITION = "position"
    COMPANY = "company"
    EDUCATION = "education"
    LOCATION = "location"
    UNKNOWN = "unknown"


class CheckType(StrEnum):
    """
    Тип проверки.

    Formal — rule-based проверки.
    Semantic — проверки через LLM/ИИ-агентов.
    """

    FORMAL = "formal"
    SEMANTIC = "semantic"
    RAG = "rag"


class CheckStatus(StrEnum):
    """
    Статус выполнения проверки отдельным агентом.
    """

    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class Severity(StrEnum):
    """
    Приоритет найденной проблемы.
    """

    CRITICAL = "Critical"
    MAJOR = "Major"
    MINOR = "Minor"


class ReportStatus(StrEnum):
    """
    Общий статус итогового отчёта.
    """

    READY = "ready"
    REQUIRES_REVISION = "requires_revision"
    FAILED = "failed"
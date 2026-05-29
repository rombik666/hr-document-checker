from typing import Any

from pydantic import BaseModel, Field


class DatabaseStatusResponse(BaseModel):
    database_available: bool
    documents_count: int
    reports_count: int
    raw_text_column_exists: bool
    pii_masking_expected: bool
    long_term_storage_contains_source_files: bool


class PrivacyCheckResponse(BaseModel):
    passed: bool
    checked_reports: int
    raw_text_column_exists: bool
    reports_with_unmasked_email: list[str]
    reports_with_unmasked_phone: list[str]
    unmasked_email_count: int
    unmasked_phone_count: int


class RoleInfo(BaseModel):
    role: str
    description: str
    permissions: list[str]


class RolesResponse(BaseModel):
    roles: list[RoleInfo]


class AdminStatusResponse(BaseModel):
    status: str
    service: str
    message: str


class BackupPayload(BaseModel):
    backup_version: str = "2.0"
    created_at: str | None = None

    documents: list[dict[str, Any]] = Field(default_factory=list)
    document_sections: list[dict[str, Any]] = Field(default_factory=list)
    processing_sessions: list[dict[str, Any]] = Field(default_factory=list)
    reports: list[dict[str, Any]] = Field(default_factory=list)
    checks: list[dict[str, Any]] = Field(default_factory=list)
    issues: list[dict[str, Any]] = Field(default_factory=list)
    recommendations: list[dict[str, Any]] = Field(default_factory=list)


class BackupRestoreResponse(BaseModel):
    restored_documents: int
    restored_document_sections: int
    restored_processing_sessions: int
    restored_reports: int
    restored_checks: int
    restored_issues: int
    restored_recommendations: int
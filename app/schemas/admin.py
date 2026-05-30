from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DatabaseStatusResponse(BaseModel):
    database_available: bool
    documents_count: int
    reports_count: int
    rag_sources_count: int = 0
    active_rag_sources_count: int = 0
    raw_text_column_exists: bool
    pii_masking_expected: bool
    long_term_storage_contains_source_files: bool


class PrivacyFinding(BaseModel):
    table_name: str
    column_name: str
    record_id: str
    finding_type: str


class PrivacyCheckResponse(BaseModel):
    passed: bool

    checked_reports: int
    checked_tables: list[str] = Field(default_factory=list)
    checked_records: int = 0

    raw_text_column_exists: bool

    reports_with_unmasked_email: list[str] = Field(default_factory=list)
    reports_with_unmasked_phone: list[str] = Field(default_factory=list)

    unmasked_email_count: int
    unmasked_phone_count: int

    findings: list[PrivacyFinding] = Field(default_factory=list)


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


class AdminRagIndexItem(BaseModel):
    owner_user_id: str
    owner_email: str | None = None
    owner_full_name: str | None = None
    owner_role: str | None = None

    status: str
    reindex_required: bool

    sources_count: int
    active_sources_count: int
    inactive_sources_count: int
    chunks_count: int

    index_exists: bool
    index_dir: str | None = None
    index_path: str | None = None
    chunks_path: str | None = None

    sources_hash: str | None = None

    embedding_backend: str | None = None
    embedding_model_name: str | None = None
    embedding_dimension: int | None = None
    retriever_type: str | None = None

    last_reindexed_at: datetime | None = None
    error_message: str | None = None


class AdminRagIndexesResponse(BaseModel):
    indexes: list[AdminRagIndexItem] = Field(default_factory=list)
    total: int
    ready_count: int = 0
    stale_count: int = 0
    missing_count: int = 0
    failed_count: int = 0
    building_count: int = 0
    reindex_required_count: int = 0


class AdminRagIndexReindexResponse(BaseModel):
    status: str
    message: str
    index: AdminRagIndexItem


class BackupDocumentItem(BaseModel):
    id: str
    owner_user_id: str | None = None
    filename: str
    document_type: str
    source_format: str
    processing_status: str
    storage_mode: str
    created_at: str | None = None


class BackupDocumentSectionItem(BaseModel):
    id: str
    document_id: str
    section_type: str
    title: str | None = None
    text: str
    position_in_document: int
    section_metadata: dict[str, Any] = Field(default_factory=dict)


class BackupProcessingSessionItem(BaseModel):
    id: str
    document_id: str
    owner_user_id: str | None = None
    status: str = "completed"
    started_at: str | None = None
    ended_at: str | None = None
    duration_ms: float | None = None
    session_metadata: dict[str, Any] = Field(default_factory=dict)


class BackupReportItem(BaseModel):
    id: str
    owner_user_id: str | None = None
    document_id: str
    processing_session_id: str | None = None
    filename: str
    summary_status: str
    total_issues: int
    critical_count: int
    major_count: int
    minor_count: int
    summary: str
    report_json: dict[str, Any]
    created_at: str | None = None


class BackupCheckItem(BaseModel):
    id: str
    processing_session_id: str
    document_id: str
    report_id: str | None = None
    agent_name: str
    check_type: str
    status: str
    started_at: str | None = None
    ended_at: str | None = None
    duration_ms: float = 0.0
    model_or_ruleset_version: str = "ruleset-1.0.0"
    error_message: str | None = None


class BackupIssueItem(BaseModel):
    id: str
    check_id: str
    document_id: str
    report_id: str
    severity: str
    issue_type: str
    description: str
    evidence_fragment: str | None = None
    source_agent: str
    confidence_score: float | None = None
    issue_metadata: dict[str, Any] = Field(default_factory=dict)


class BackupRecommendationItem(BaseModel):
    id: str
    issue_id: str
    recommendation_text: str
    example_fix: str | None = None
    priority_order: int = 0


class BackupRagSourceItem(BaseModel):
    id: str
    owner_user_id: str | None = None
    title: str
    filename: str
    source_type: str
    source_format: str
    content: str
    content_hash: str
    file_size_bytes: int = 0
    is_active: bool = True
    source_metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None
    updated_at: str | None = None


class BackupPayload(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "backup_version": "2.0",
                "created_at": None,
                "documents": [],
                "document_sections": [],
                "processing_sessions": [],
                "reports": [],
                "checks": [],
                "issues": [],
                "recommendations": [],
                "rag_sources": [],
            }
        }
    )

    backup_version: str = "2.0"
    created_at: str | None = None

    documents: list[BackupDocumentItem] = Field(default_factory=list)
    document_sections: list[BackupDocumentSectionItem] = Field(default_factory=list)
    processing_sessions: list[BackupProcessingSessionItem] = Field(default_factory=list)
    reports: list[BackupReportItem] = Field(default_factory=list)
    checks: list[BackupCheckItem] = Field(default_factory=list)
    issues: list[BackupIssueItem] = Field(default_factory=list)
    recommendations: list[BackupRecommendationItem] = Field(default_factory=list)
    rag_sources: list[BackupRagSourceItem] = Field(default_factory=list)


class BackupRestoreResponse(BaseModel):
    restored_documents: int
    restored_document_sections: int
    restored_processing_sessions: int
    restored_reports: int
    restored_checks: int
    restored_issues: int
    restored_recommendations: int
    restored_rag_sources: int = 0
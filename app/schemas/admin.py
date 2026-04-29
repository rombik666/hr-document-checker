from pydantic import BaseModel


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
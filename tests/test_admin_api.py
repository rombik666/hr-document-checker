from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db.models import DocumentORM, RagIndexORM, RagSourceORM, UserORM
from app.db.session import SessionLocal
from app.main import app
from tests.auth_helpers import admin_auth_headers, auth_headers


client = TestClient(app)


def test_admin_status_endpoint_returns_ok() -> None:
    response = client.get(
        "/api/v1/admin/status",
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"
    assert data["service"] == "admin"


def test_admin_roles_endpoint_returns_roles() -> None:
    response = client.get(
        "/api/v1/admin/roles",
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200

    data = response.json()
    roles = {
        item["role"]
        for item in data["roles"]
    }

    assert "candidate" in roles
    assert "hr" in roles
    assert "admin" in roles

    admin_permissions = next(
        item["permissions"]
        for item in data["roles"]
        if item["role"] == "admin"
    )

    assert "list_rag_indexes" in admin_permissions
    assert "reindex_any_rag_index" in admin_permissions


def test_admin_database_status_endpoint_returns_diagnostics() -> None:
    response = client.get(
        "/api/v1/admin/db/status",
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["database_available"] is True
    assert "documents_count" in data
    assert "reports_count" in data
    assert "rag_sources_count" in data
    assert "active_rag_sources_count" in data
    assert data["raw_text_column_exists"] is False
    assert "rag_indexes_count" in data
    assert "ready_rag_indexes_count" in data
    assert "stale_rag_indexes_count" in data
    assert "missing_rag_indexes_count" in data
    assert "failed_rag_indexes_count" in data
    assert "building_rag_indexes_count" in data
    assert "rag_indexes_reindex_required_count" in data


def test_admin_privacy_check_endpoint_returns_result() -> None:
    response = client.get(
        "/api/v1/admin/storage/privacy-check",
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200

    data = response.json()

    assert "passed" in data
    assert "checked_reports" in data
    assert "unmasked_email_count" in data
    assert "unmasked_phone_count" in data
    assert data["raw_text_column_exists"] is False


def test_admin_backup_endpoint_returns_normalized_payload() -> None:
    response = client.get(
        "/api/v1/admin/backup",
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["backup_version"] == "2.0"
    assert "documents" in data
    assert "document_sections" in data
    assert "processing_sessions" in data
    assert "reports" in data
    assert "checks" in data
    assert "issues" in data
    assert "recommendations" in data
    assert "rag_sources" in data
    assert "rag_indexes" in data


def test_admin_restore_endpoint_accepts_empty_backup_payload() -> None:
    payload = {
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
        "rag_indexes": [],
    }

    response = client.post(
        "/api/v1/admin/restore",
        json=payload,
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["restored_documents"] == 0
    assert data["restored_document_sections"] == 0
    assert data["restored_processing_sessions"] == 0
    assert data["restored_reports"] == 0
    assert data["restored_checks"] == 0
    assert data["restored_issues"] == 0
    assert data["restored_recommendations"] == 0
    assert data["restored_rag_sources"] == 0
    assert data["restored_rag_indexes"] == 0


def test_admin_backup_endpoint_forbids_non_admin_user() -> None:
    response = client.get(
        "/api/v1/admin/backup",
        headers=auth_headers(client, role="candidate"),
    )

    assert response.status_code == 403


def test_admin_restore_endpoint_rejects_invalid_backup_payload() -> None:
    payload = {
        "backup_version": "2.0",
        "created_at": "string",
        "documents": [
            {
                "additionalProp1": {},
            }
        ],
        "document_sections": [],
        "processing_sessions": [],
        "reports": [],
        "checks": [],
        "issues": [],
        "recommendations": [],
        "rag_sources": [],
    }

    response = client.post(
        "/api/v1/admin/restore",
        json=payload,
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 422


def test_admin_restore_endpoint_accepts_current_backup_payload() -> None:
    backup_response = client.get(
        "/api/v1/admin/backup",
        headers=admin_auth_headers(client),
    )

    assert backup_response.status_code == 200

    restore_response = client.post(
        "/api/v1/admin/restore",
        json=backup_response.json(),
        headers=admin_auth_headers(client),
    )

    assert restore_response.status_code == 200

    data = restore_response.json()

    assert "restored_documents" in data
    assert "restored_document_sections" in data
    assert "restored_processing_sessions" in data
    assert "restored_reports" in data
    assert "restored_checks" in data
    assert "restored_issues" in data
    assert "restored_recommendations" in data
    assert "restored_rag_sources" in data
    assert "restored_rag_indexes" in data


def test_admin_restore_endpoint_rejects_swagger_placeholder_payload() -> None:
    payload = {
        "backup_version": "2.0",
        "created_at": "string",
        "documents": [
            {
                "id": "string",
                "owner_user_id": "string",
                "filename": "string",
                "document_type": "string",
                "source_format": "string",
                "processing_status": "string",
                "storage_mode": "string",
                "created_at": "string",
            }
        ],
        "document_sections": [],
        "processing_sessions": [],
        "reports": [],
        "checks": [],
        "issues": [],
        "recommendations": [],
        "rag_sources": [],
        "rag_indexes": [],
    }

    response = client.post(
        "/api/v1/admin/restore",
        json=payload,
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 422


def test_admin_privacy_check_detects_unmasked_normalized_storage_value() -> None:
    db = SessionLocal()
    document_id = "privacy-check-leak-document"

    try:
        db.execute(delete(DocumentORM).where(DocumentORM.id == document_id))

        db.add(
            DocumentORM(
                id=document_id,
                owner_user_id=None,
                filename="ivan@example.com_resume.docx",
                document_type="cv",
                source_format="docx",
                processing_status="report_generated",
                storage_mode="temporary",
            )
        )

        db.commit()

        response = client.get(
            "/api/v1/admin/storage/privacy-check",
            headers=admin_auth_headers(client),
        )

        assert response.status_code == 200

        data = response.json()

        assert data["passed"] is False
        assert data["unmasked_email_count"] >= 1
        assert "documents" in data["checked_tables"]

        findings = data["findings"]

        assert any(
            finding["table_name"] == "documents"
            and finding["column_name"] == "filename"
            and finding["record_id"] == document_id
            and finding["finding_type"] == "email"
            for finding in findings
        )

    finally:
        db.execute(delete(DocumentORM).where(DocumentORM.id == document_id))
        db.commit()
        db.close()


def test_admin_privacy_check_detects_unmasked_rag_source_value() -> None:
    db = SessionLocal()
    source_id = "privacy-check-leak-rag-source"

    try:
        db.execute(delete(RagSourceORM).where(RagSourceORM.id == source_id))

        db.add(
            RagSourceORM(
                id=source_id,
                owner_user_id=None,
                title="RAG source with ivan@example.com",
                filename="rag_source.txt",
                source_type="requirements",
                source_format="txt",
                content="Контакт HR: ivan@example.com, телефон +7 999 123-45-67.",
                content_hash="privacy-check-rag-source-hash",
                file_size_bytes=128,
                is_active=True,
                source_metadata={},
            )
        )

        db.commit()

        response = client.get(
            "/api/v1/admin/storage/privacy-check",
            headers=admin_auth_headers(client),
        )

        assert response.status_code == 200

        data = response.json()

        assert data["passed"] is False
        assert data["unmasked_email_count"] >= 1
        assert data["unmasked_phone_count"] >= 1
        assert "rag_sources" in data["checked_tables"]

        findings = data["findings"]

        assert any(
            finding["table_name"] == "rag_sources"
            and finding["column_name"] in {"title", "content"}
            and finding["record_id"] == source_id
            and finding["finding_type"] == "email"
            for finding in findings
        )

        assert any(
            finding["table_name"] == "rag_sources"
            and finding["column_name"] == "content"
            and finding["record_id"] == source_id
            and finding["finding_type"] == "phone"
            for finding in findings
        )

    finally:
        db.execute(delete(RagSourceORM).where(RagSourceORM.id == source_id))
        db.commit()
        db.close()

def test_admin_privacy_check_detects_unmasked_rag_index_metadata() -> None:
    db = SessionLocal()

    user_id = "privacy-check-rag-index-user"
    index_id = "privacy-check-leak-rag-index"

    try:
        db.execute(delete(RagIndexORM).where(RagIndexORM.id == index_id))
        db.execute(delete(UserORM).where(UserORM.id == user_id))

        db.add(
            UserORM(
                id=user_id,
                email="privacy-rag-index-user@example.test",
                full_name="Privacy RAG Index User",
                role="hr",
                password_hash="test-password-hash",
                is_active=True,
            )
        )

        db.add(
            RagIndexORM(
                id=index_id,
                owner_user_id=user_id,
                status="failed",
                reindex_required=True,
                index_path="/app/data/index/users/privacy-check/faiss.index",
                chunks_path="/app/data/index/users/privacy-check/chunks.json",
                sources_hash="privacy-check-rag-index-hash",
                sources_count=1,
                chunks_count=0,
                embedding_backend="hashing",
                embedding_model_name="hashing",
                embedding_dimension=384,
                retriever_type="faiss",
                index_metadata={
                    "debug_contact": "ivan@example.com",
                },
                error_message="Ошибка обработки источника, телефон +7 999 123-45-67.",
            )
        )

        db.commit()

        response = client.get(
            "/api/v1/admin/storage/privacy-check",
            headers=admin_auth_headers(client),
        )

        assert response.status_code == 200

        data = response.json()

        assert data["passed"] is False
        assert data["unmasked_email_count"] >= 1
        assert data["unmasked_phone_count"] >= 1
        assert "rag_indexes" in data["checked_tables"]

        findings = data["findings"]

        assert any(
            finding["table_name"] == "rag_indexes"
            and finding["column_name"] == "index_metadata"
            and finding["record_id"] == index_id
            and finding["finding_type"] == "email"
            for finding in findings
        )

        assert any(
            finding["table_name"] == "rag_indexes"
            and finding["column_name"] == "error_message"
            and finding["record_id"] == index_id
            and finding["finding_type"] == "phone"
            for finding in findings
        )

    finally:
        db.execute(delete(RagIndexORM).where(RagIndexORM.id == index_id))
        db.execute(delete(UserORM).where(UserORM.id == user_id))
        db.commit()
        db.close()
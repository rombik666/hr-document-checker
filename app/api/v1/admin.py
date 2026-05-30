from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.db.models import UserORM
from app.db.session import get_db
from app.rag.service import RagService
from app.schemas.rag import (
    RagReindexResponse,
    RagSourceInfo,
    RagSourcesResponse,
    RagStatus,
)
from app.schemas.admin import (
    AdminStatusResponse,
    BackupPayload,
    BackupRestoreResponse,
    DatabaseStatusResponse,
    PrivacyCheckResponse,
    RoleInfo,
    RolesResponse,
)
from app.services.backup_service import BackupService
from app.services.db_inspection_service import DbInspectionService

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from app.services.rag_source_service import RagSourceService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/status", response_model=AdminStatusResponse)
def get_admin_status(
    current_user: UserORM = Depends(require_admin),
) -> AdminStatusResponse:
    return AdminStatusResponse(
        status="ok",
        service="admin",
        message="Administrative diagnostics are available.",
    )


@router.get("/roles", response_model=RolesResponse)
def get_roles(
    current_user: UserORM = Depends(require_admin),
) -> RolesResponse:
    return RolesResponse(
        roles=[
            RoleInfo(
                role="candidate",
                description="Uploads documents and receives recommendations.",
                permissions=[
                    "upload_document",
                    "view_own_report",
                    "export_report",
                ],
            ),
            RoleInfo(
                role="hr",
                description="Checks candidate documents and reviews reports.",
                permissions=[
                    "upload_document",
                    "view_report",
                    "compare_with_vacancy",
                    "export_report",
                ],
            ),
            RoleInfo(
                role="admin",
                description="Monitors system status, metrics, backups and storage diagnostics.",
                permissions=[
                    "view_rag_status",
                    "list_rag_sources",
                    "reindex_rag",                    
                    "view_metrics",
                    "view_database_status",
                    "run_privacy_check",
                    "create_backup",
                    "restore_backup",
                ],
            ),
        ]
    )


@router.get("/db/status", response_model=DatabaseStatusResponse)
def get_database_status(
    db: Session = Depends(get_db),
    current_user: UserORM = Depends(require_admin),
) -> DatabaseStatusResponse:
    service = DbInspectionService(db)
    return DatabaseStatusResponse.model_validate(
        service.get_database_status()
    )


@router.get("/storage/privacy-check", response_model=PrivacyCheckResponse)
def run_storage_privacy_check(
    db: Session = Depends(get_db),
    current_user: UserORM = Depends(require_admin),
) -> PrivacyCheckResponse:
    service = DbInspectionService(db)
    return PrivacyCheckResponse.model_validate(
        service.run_privacy_check()
    )

@router.get("/rag/status", response_model=RagStatus)
def get_admin_rag_status(
    db: Session = Depends(get_db),
    current_user: UserORM = Depends(require_admin),
) -> RagStatus:
    service = RagService()

    return service.get_user_sources_status(
        db=db,
        user_id=current_user.id,
        user_role=current_user.role,
    )


@router.get("/rag/sources", response_model=RagSourcesResponse)
def list_admin_rag_sources(
    db: Session = Depends(get_db),
    current_user: UserORM = Depends(require_admin),
) -> RagSourcesResponse:

    service = RagSourceService(db)

    sources = service.list_sources_for_user(
        user_id=current_user.id,
        user_role=current_user.role,
        include_inactive=True,
        limit=1000,
    )

    return RagSourcesResponse(
        knowledge_base_dir="database://rag_sources",
        sources_count=len(sources),
        sources=[
            RagSourceInfo(
                source_id=source.id,
                title=source.title,
                path=f"db://rag_sources/{source.id}",
                content_length=len(source.content),
            )
            for source in sources
        ],
    )


@router.post("/rag/reindex", response_model=RagReindexResponse)
def reindex_admin_rag(
    db: Session = Depends(get_db),
    current_user: UserORM = Depends(require_admin),
) -> RagReindexResponse:

    rag_service = RagService()
    source_service = RagSourceService(db)

    sources = source_service.list_sources_for_user(
        user_id=current_user.id,
        user_role=current_user.role,
        include_inactive=True,
        limit=1000,
    )

    active_sources = [
        source
        for source in sources
        if source.is_active
    ]

    rag_sources = [
        source_service.to_rag_source(source)
        for source in active_sources
    ]

    chunks = rag_service.chunker.chunk_sources(rag_sources)

    return RagReindexResponse(
        status="not_required",
        message=(
            "DB-backed RAG uses dynamic in-memory retrieval; "
            "FAISS reindex is not required."
        ),
        mode="db_sources",
        source_backend="database",
        sources_count=len(sources),
        active_sources_count=len(active_sources),
        chunks_count=len(chunks),
        embedding_dimension=rag_service.embedding_model.dimension,
        index_path=None,
        chunks_path=None,
    )


@router.get("/backup", response_model=BackupPayload)
def create_backup(
    db: Session = Depends(get_db),
    current_user: UserORM = Depends(require_admin),
) -> BackupPayload:
    """
    Формирует JSON-backup нормализованной БД.

    Backup включает документы, секции, сессии обработки,
    отчёты, проверки, замечания и рекомендации.
    """
    service = BackupService(db)
    return BackupPayload.model_validate(
        service.create_backup_payload()
    )


@router.post("/restore", response_model=BackupRestoreResponse)
def restore_backup(
    payload: BackupPayload,
    db: Session = Depends(get_db),
    current_user: UserORM = Depends(require_admin),
) -> BackupRestoreResponse:
    """
    Восстанавливает данные из JSON-backup.

    Restore идемпотентен: уже существующие записи не дублируются.
    """
    service = BackupService(db)

    try:
        result = service.restore_from_payload(
            payload.model_dump(mode="json")
        )
    except KeyError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Invalid backup payload: missing required field {error}",
        ) from error
    except (ValueError, TypeError) as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Invalid backup payload value: {error}",
        ) from error
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Backup restore failed because of database integrity error: {error}",
        ) from error

    return BackupRestoreResponse.model_validate(result)
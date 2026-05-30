from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.db.models import UserORM
from app.db.session import get_db
from app.schemas.admin import (
    AdminRagIndexItem,
    AdminRagIndexReindexResponse,
    AdminRagIndexesResponse,
    AdminStatusResponse,
    BackupPayload,
    BackupRestoreResponse,
    DatabaseStatusResponse,
    PrivacyCheckResponse,
    RoleInfo,
    RolesResponse,
)
from app.schemas.rag import (
    RagReindexResponse,
    RagSourceInfo,
    RagSourcesResponse,
    RagStatus,
)
from app.services.backup_service import BackupService
from app.services.db_inspection_service import DbInspectionService
from app.services.rag_index_service import RagIndexService
from app.services.rag_source_service import RagSourceService


router = APIRouter(prefix="/admin", tags=["admin"])


def _admin_rag_index_item_from_status(
    user: UserORM,
    rag_status: RagStatus,
) -> AdminRagIndexItem:
    return AdminRagIndexItem(
        owner_user_id=user.id,
        owner_email=user.email,
        owner_full_name=user.full_name,
        owner_role=user.role,
        status=rag_status.index_status,
        reindex_required=rag_status.reindex_required,
        sources_count=rag_status.sources_count,
        active_sources_count=rag_status.active_sources_count,
        inactive_sources_count=rag_status.inactive_sources_count,
        chunks_count=rag_status.chunks_count,
        index_exists=rag_status.index_exists,
        index_dir=rag_status.index_dir,
        index_path=rag_status.index_path,
        chunks_path=rag_status.chunks_path,
        sources_hash=rag_status.sources_hash,
        embedding_backend=rag_status.embedding_backend,
        embedding_model_name=rag_status.embedding_model_name,
        embedding_dimension=rag_status.embedding_dimension,
        retriever_type=rag_status.retriever_type,
        last_reindexed_at=rag_status.last_reindexed_at,
        error_message=rag_status.index_error,
    )


def _get_rag_user_or_404(
    db: Session,
    user_id: str,
) -> UserORM:
    user = db.get(UserORM, user_id)

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found.",
        )

    if user.role not in {"hr", "admin"}:
        raise HTTPException(
            status_code=400,
            detail="RAG indexes are available only for HR and admin users.",
        )

    return user


def _count_index_statuses(items: list[AdminRagIndexItem]) -> dict[str, int]:
    return {
        "ready_count": sum(1 for item in items if item.status == "ready"),
        "stale_count": sum(1 for item in items if item.status == "stale"),
        "missing_count": sum(1 for item in items if item.status == "missing"),
        "failed_count": sum(1 for item in items if item.status == "failed"),
        "building_count": sum(1 for item in items if item.status == "building"),
        "reindex_required_count": sum(
            1
            for item in items
            if item.reindex_required
        ),
    }


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
                description="Checks candidate documents, manages own RAG sources and reviews reports.",
                permissions=[
                    "upload_document",
                    "view_report",
                    "compare_with_vacancy",
                    "export_report",
                    "manage_own_rag_sources",
                    "reindex_own_rag_index",
                ],
            ),
            RoleInfo(
                role="admin",
                description="Monitors system status, metrics, backups, storage diagnostics and RAG indexes.",
                permissions=[
                    "view_rag_status",
                    "list_rag_sources",
                    "list_rag_indexes",
                    "reindex_any_rag_index",
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
    """
    Возвращает статус персонального FAISS-индекса текущего admin-пользователя.
    Для просмотра всех индексов используется /admin/rag/indexes.
    """

    service = RagIndexService(db)

    return service.get_user_status(
        owner_user_id=current_user.id,
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
def reindex_admin_own_rag(
    db: Session = Depends(get_db),
    current_user: UserORM = Depends(require_admin),
) -> RagReindexResponse:
    """
    Совместимый endpoint для переиндексации собственного admin FAISS-индекса.

    Новый основной admin-контур для любого пользователя:
    POST /api/v1/admin/rag/indexes/{user_id}/reindex
    """

    service = RagIndexService(db)
    rag_index = service.reindex_user_sources(
        owner_user_id=current_user.id,
    )

    return RagReindexResponse(
        status="completed",
        message="Admin personal RAG FAISS index was rebuilt successfully.",
        mode="per_user_faiss",
        source_backend="database+filesystem",
        sources_count=rag_index.sources_count,
        active_sources_count=rag_index.sources_count,
        chunks_count=rag_index.chunks_count,
        embedding_dimension=rag_index.embedding_dimension,
        index_path=rag_index.index_path,
        chunks_path=rag_index.chunks_path,
    )


@router.get("/rag/indexes", response_model=AdminRagIndexesResponse)
def list_admin_rag_indexes(
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: UserORM = Depends(require_admin),
) -> AdminRagIndexesResponse:
    """
    Показывает состояние персональных FAISS-индексов HR/admin пользователей.
    """

    users = list(
        db.execute(
            select(UserORM)
            .where(UserORM.role.in_(["hr", "admin"]))
            .order_by(UserORM.role.asc(), UserORM.email.asc())
            .limit(limit)
        )
        .scalars()
        .all()
    )

    service = RagIndexService(db)

    items = [
        _admin_rag_index_item_from_status(
            user=user,
            rag_status=service.get_user_status(user.id),
        )
        for user in users
    ]

    counts = _count_index_statuses(items)

    return AdminRagIndexesResponse(
        indexes=items,
        total=len(items),
        **counts,
    )


@router.get("/rag/indexes/{user_id}", response_model=AdminRagIndexItem)
def get_admin_rag_index(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: UserORM = Depends(require_admin),
) -> AdminRagIndexItem:
    """
    Показывает состояние персонального FAISS-индекса конкретного HR/admin.
    """

    user = _get_rag_user_or_404(
        db=db,
        user_id=user_id,
    )

    service = RagIndexService(db)

    return _admin_rag_index_item_from_status(
        user=user,
        rag_status=service.get_user_status(user.id),
    )


@router.post("/rag/indexes/{user_id}/reindex", response_model=AdminRagIndexReindexResponse)
def reindex_admin_rag_index(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: UserORM = Depends(require_admin),
) -> AdminRagIndexReindexResponse:
    """
    Перестраивает персональный FAISS-индекс выбранного HR/admin пользователя.
    """

    user = _get_rag_user_or_404(
        db=db,
        user_id=user_id,
    )

    service = RagIndexService(db)

    try:
        service.reindex_user_sources(
            owner_user_id=user.id,
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"RAG reindex failed for user {user.id}: {error}",
        ) from error

    item = _admin_rag_index_item_from_status(
        user=user,
        rag_status=service.get_user_status(user.id),
    )

    return AdminRagIndexReindexResponse(
        status="completed",
        message="User RAG FAISS index was rebuilt successfully.",
        index=item,
    )


@router.get("/backup", response_model=BackupPayload)
def create_backup(
    db: Session = Depends(get_db),
    current_user: UserORM = Depends(require_admin),
) -> BackupPayload:
    """
    Формирует JSON-backup нормализованной БД.
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
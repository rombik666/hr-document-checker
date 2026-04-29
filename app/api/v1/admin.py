from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.admin import (
    AdminStatusResponse,
    DatabaseStatusResponse,
    PrivacyCheckResponse,
    RoleInfo,
    RolesResponse,
)
from app.services.db_inspection_service import DbInspectionService

from fastapi import Depends

from app.auth.dependencies import require_admin
from app.db.models import UserORM


router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/status", response_model=AdminStatusResponse)
def get_admin_status(current_user: UserORM = Depends(require_admin),) -> AdminStatusResponse:

    return AdminStatusResponse(
        status="ok",
        service="admin",
        message="Administrative diagnostics are available.",
    )


@router.get("/roles", response_model=RolesResponse)
def get_roles(current_user: UserORM = Depends(require_admin),) -> RolesResponse:

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
                description="Monitors system status, metrics and storage diagnostics.",
                permissions=[
                    "view_metrics",
                    "view_database_status",
                    "run_privacy_check",
                    "run_backup_restore",
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
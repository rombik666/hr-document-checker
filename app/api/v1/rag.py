from pathlib import Path
from tempfile import NamedTemporaryFile
from app.db.session import get_db

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.auth.dependencies import require_hr_or_admin
from app.db.models import UserORM
from app.db.session import get_db
from app.rag.service import RagService
from app.schemas.rag import (
    RagContext,
    RagSearchRequest,
    RagStatus,
    UserRagSourceDeleteResponse,
    UserRagSourceDetails,
    UserRagSourcesListResponse,
    UserRagSourceUploadResponse,
)
from app.services.rag_source_service import RagSourceService


router = APIRouter(prefix="/rag", tags=["rag"])


async def _save_upload_to_temp_file(file: UploadFile, suffix: str) -> tuple[Path, int]:
    content = await file.read()
    file_size_bytes = len(content)

    if file_size_bytes > RagSourceService.MAX_SINGLE_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=(
                "RAG source file is too large. "
                "Maximum allowed file size is 15 MB."
            ),
        )

    with NamedTemporaryFile(delete=False, suffix=suffix) as temporary_file:
        temporary_file.write(content)

        return Path(temporary_file.name), file_size_bytes


def _validate_rag_source_filename(filename: str) -> str:
    suffix = Path(filename).suffix.lower()

    if suffix not in RagSourceService.SUPPORTED_SUFFIXES:
        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported RAG source format. "
                "Supported formats: .docx, .pdf, .txt, .md."
            ),
        )

    return suffix


@router.post("/search", response_model=RagContext)
def search_rag_context(
    request: RagSearchRequest,
    current_user: UserORM = Depends(require_hr_or_admin),
    db: Session = Depends(get_db),
) -> RagContext:
    service = RagService()

    return service.search_user_sources(
        request=request,
        db=db,
        user_id=current_user.id,
        user_role=current_user.role,
    )


@router.get("/status", response_model=RagStatus)
def get_rag_status(
    current_user: UserORM = Depends(require_hr_or_admin),
    db: Session = Depends(get_db),
) -> RagStatus:
    service = RagService()

    return service.get_user_sources_status(
        db=db,
        user_id=current_user.id,
        user_role=current_user.role,
    )


@router.post("/sources/upload", response_model=UserRagSourceUploadResponse)
async def upload_rag_source(
    file: UploadFile = File(...),
    title: str | None = Form(None),
    source_type: str = Form("other"),
    current_user: UserORM = Depends(require_hr_or_admin),
    db: Session = Depends(get_db),
) -> UserRagSourceUploadResponse:
    """
    Загружает пользовательский RAG-источник.

    HR может загружать документы своей компании: вакансии, чек-листы,
    регламенты и требования. Admin также может загружать источники.
    """

    original_filename = file.filename or ""

    if not original_filename:
        raise HTTPException(
            status_code=400,
            detail="Filename is required.",
        )

    suffix = _validate_rag_source_filename(original_filename)
    temporary_path: Path | None = None

    try:
        temporary_path, file_size_bytes = await _save_upload_to_temp_file(
            file,
            suffix,
        )

        service = RagSourceService(db)
        source = service.create_source_from_file(
            file_path=temporary_path,
            original_filename=original_filename,
            owner_user_id=current_user.id,
            title=title,
            source_type=source_type,
            file_size_bytes=file_size_bytes,
        )

        return UserRagSourceUploadResponse(
            source=service.to_details(source),
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


@router.get("/sources", response_model=UserRagSourcesListResponse)
def list_rag_sources(
    include_inactive: bool = Query(False),
    limit: int = Query(100, ge=1, le=1000),
    current_user: UserORM = Depends(require_hr_or_admin),
    db: Session = Depends(get_db),
) -> UserRagSourcesListResponse:
    """
    Возвращает список RAG-источников пользователя.

    HR видит только свои источники.
    Admin видит все источники.
    """

    service = RagSourceService(db)

    sources = service.list_sources_for_user(
        user_id=current_user.id,
        user_role=current_user.role,
        include_inactive=include_inactive,
        limit=limit,
    )

    return UserRagSourcesListResponse(
        sources_count=len(sources),
        sources=[
            service.to_list_item(source)
            for source in sources
        ],
    )


@router.get("/sources/{source_id}", response_model=UserRagSourceDetails)
def get_rag_source(
    source_id: str,
    current_user: UserORM = Depends(require_hr_or_admin),
    db: Session = Depends(get_db),
) -> UserRagSourceDetails:
    """
    Возвращает RAG-источник по ID.

    HR может открыть только свой источник.
    Admin может открыть любой источник.
    """

    service = RagSourceService(db)

    source = service.get_source_for_user(
        source_id=source_id,
        user_id=current_user.id,
        user_role=current_user.role,
    )

    if source is None:
        raise HTTPException(
            status_code=404,
            detail="RAG source not found.",
        )

    return service.to_details(source)


@router.delete("/sources/{source_id}", response_model=UserRagSourceDeleteResponse)
def delete_rag_source(
    source_id: str,
    current_user: UserORM = Depends(require_hr_or_admin),
    db: Session = Depends(get_db),
) -> UserRagSourceDeleteResponse:
    """
    Деактивирует RAG-источник.

    Физически запись не удаляется, чтобы сохранить историю и возможность аудита.
    """

    service = RagSourceService(db)

    deleted = service.deactivate_source_for_user(
        source_id=source_id,
        user_id=current_user.id,
        user_role=current_user.role,
    )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="RAG source not found.",
        )

    return UserRagSourceDeleteResponse(
        source_id=source_id,
        deleted=True,
        message="RAG source was deactivated.",
    )
from pathlib import Path
from tempfile import NamedTemporaryFile

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
    UserRagReindexResponse,
    UserRagSourceActionResponse,
    UserRagSourceDeleteResponse,
    UserRagSourceDetails,
    UserRagSourcesListResponse,
    UserRagSourceUploadResponse,
)
from app.services.rag_index_service import RagIndexNotReadyError, RagIndexService
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
    """
    Ищет RAG-контекст только по готовому персональному FAISS-индексу.

    Если индекс отсутствует или устарел, возвращает HTTP 409
    с требованием выполнить POST /api/v1/rag/reindex.
    """

    service = RagIndexService(db)

    try:
        return service.search_user_index(
            owner_user_id=current_user.id,
            request=request,
        )

    except RagIndexNotReadyError as error:
        raise HTTPException(
            status_code=409,
            detail=error.to_detail(),
        ) from error


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


@router.post("/reindex", response_model=UserRagReindexResponse)
def reindex_current_user_rag(
    current_user: UserORM = Depends(require_hr_or_admin),
    db: Session = Depends(get_db),
) -> UserRagReindexResponse:
    """
    Строит или перестраивает персональный FAISS-индекс текущего HR/admin.

    Индекс строится только по активным rag_sources текущего пользователя.
    Candidate не имеет доступа к этому endpoint.
    """

    service = RagIndexService(db)

    try:
        rag_index = service.reindex_user_sources(
            owner_user_id=current_user.id,
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"RAG reindex failed: {error}",
        ) from error

    return UserRagReindexResponse(
        status="completed",
        message="Personal RAG FAISS index was rebuilt successfully.",
        owner_user_id=rag_index.owner_user_id,
        sources_count=rag_index.sources_count,
        chunks_count=rag_index.chunks_count,
        index_path=rag_index.index_path,
        chunks_path=rag_index.chunks_path,
        sources_hash=rag_index.sources_hash,
        reindex_required=rag_index.reindex_required,
        embedding_backend=rag_index.embedding_backend,
        embedding_model_name=rag_index.embedding_model_name,
        embedding_dimension=rag_index.embedding_dimension,
        retriever_type=rag_index.retriever_type,
        last_reindexed_at=rag_index.last_reindexed_at,
    )


@router.post("/sources/upload", response_model=UserRagSourceUploadResponse)
async def upload_rag_source(
    file: UploadFile = File(...),
    title: str | None = Form(None),
    source_type: str = Form("other"),
    current_user: UserORM = Depends(require_hr_or_admin),
    db: Session = Depends(get_db),
) -> UserRagSourceUploadResponse:
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


@router.post("/sources/{source_id}/activate", response_model=UserRagSourceActionResponse)
def activate_rag_source(
    source_id: str,
    current_user: UserORM = Depends(require_hr_or_admin),
    db: Session = Depends(get_db),
) -> UserRagSourceActionResponse:
    service = RagSourceService(db)

    try:
        activated = service.activate_source_for_user(
            source_id=source_id,
            user_id=current_user.id,
            user_role=current_user.role,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    if not activated:
        raise HTTPException(
            status_code=404,
            detail="RAG source not found.",
        )

    return UserRagSourceActionResponse(
        source_id=source_id,
        action="activate",
        success=True,
        message="RAG source was activated.",
    )


@router.delete("/sources/{source_id}/permanent", response_model=UserRagSourceActionResponse)
def permanently_delete_rag_source(
    source_id: str,
    current_user: UserORM = Depends(require_hr_or_admin),
    db: Session = Depends(get_db),
) -> UserRagSourceActionResponse:
    service = RagSourceService(db)

    deleted = service.permanently_delete_source_for_user(
        source_id=source_id,
        user_id=current_user.id,
        user_role=current_user.role,
    )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="RAG source not found.",
        )

    return UserRagSourceActionResponse(
        source_id=source_id,
        action="permanent_delete",
        success=True,
        message="RAG source was permanently deleted.",
    )
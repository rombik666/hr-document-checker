from pathlib import Path
from tempfile import NamedTemporaryFile
from time import perf_counter

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import require_candidate_or_hr_or_admin
from app.coordinator.formal_check_coordinator import FormalCheckCoordinator
from app.coordinator.semantic_check_coordinator import SemanticCheckCoordinator
from app.core.logging import get_logger
from app.core.metrics import metrics
from app.db.models import UserORM
from app.db.session import get_db
from app.reports.docx_exporter import DocxReportExporter
from app.reports.report_builder import ReportBuilder
from app.schemas.checks import FormalCheckResponse, SemanticCheckResponse
from app.schemas.common import StorageMode
from app.schemas.documents import ParsedDocument
from app.schemas.reports import Report
from app.services.document_processing_service import DocumentProcessingService
from app.services.report_storage_service import ReportStorageService


logger = get_logger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


def _validate_file_suffix(filename: str) -> str:
    suffix = Path(filename).suffix.lower()

    if suffix not in {".docx", ".pdf"}:
        raise HTTPException(
            status_code=400,
            detail="Поддерживаются только файлы .docx и .pdf",
        )

    return suffix


async def _save_upload_to_temp_file(file: UploadFile, suffix: str) -> Path:
    with NamedTemporaryFile(delete=False, suffix=suffix) as temporary_file:
        content = await file.read()
        temporary_file.write(content)
        return Path(temporary_file.name)


def _ensure_report_access(
    storage_service: ReportStorageService,
    report_id: str,
    current_user: UserORM,
) -> None:
    can_access = storage_service.user_can_access_report(
        report_id=report_id,
        user_id=current_user.id,
        user_role=current_user.role,
    )

    if not can_access:
        raise HTTPException(
            status_code=404,
            detail="Отчёт не найден",
        )


@router.post("/parse", response_model=ParsedDocument)
async def parse_document(
    file: UploadFile = File(...),
    storage_mode: StorageMode = Form(StorageMode.TEMPORARY),
    current_user: UserORM = Depends(require_candidate_or_hr_or_admin),
) -> ParsedDocument:
    """
    Загружает DOCX/PDF-файл, извлекает текст, секции и сущности.
    Доступно только авторизованным пользователям.
    """

    filename = file.filename or ""
    suffix = _validate_file_suffix(filename)

    temporary_path: Path | None = None

    try:
        temporary_path = await _save_upload_to_temp_file(file, suffix)

        service = DocumentProcessingService()
        parsed_document = service.parse_and_enrich(
            file_path=temporary_path,
            original_filename=filename,
            storage_mode=storage_mode,
        )

        return parsed_document

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при парсинге документа: {error}",
        ) from error

    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()


@router.post("/check-formal", response_model=FormalCheckResponse)
async def check_document_formally(
    file: UploadFile = File(...),
    storage_mode: StorageMode = Form(StorageMode.TEMPORARY),
    current_user: UserORM = Depends(require_candidate_or_hr_or_admin),
) -> FormalCheckResponse:
    """
    Загружает DOCX/PDF-файл и выполняет формальные rule-based проверки.
    Доступно только авторизованным пользователям.
    """

    filename = file.filename or ""
    suffix = _validate_file_suffix(filename)

    temporary_path: Path | None = None

    try:
        temporary_path = await _save_upload_to_temp_file(file, suffix)

        service = DocumentProcessingService()
        parsed_document = service.parse_and_enrich(
            file_path=temporary_path,
            original_filename=filename,
            storage_mode=storage_mode,
        )

        coordinator = FormalCheckCoordinator()
        result = coordinator.run(parsed_document)

        return result

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при формальной проверке документа: {error}",
        ) from error

    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()


@router.post("/check-semantic", response_model=SemanticCheckResponse)
async def check_document_semantically(
    file: UploadFile = File(...),
    vacancy_text: str | None = Form(None),
    storage_mode: StorageMode = Form(StorageMode.TEMPORARY),
    current_user: UserORM = Depends(require_candidate_or_hr_or_admin),
) -> SemanticCheckResponse:
    """
    Загружает DOCX/PDF-файл и выполняет семантические проверки.
    Доступно только авторизованным пользователям.
    """

    filename = file.filename or ""
    suffix = _validate_file_suffix(filename)

    temporary_path: Path | None = None

    try:
        temporary_path = await _save_upload_to_temp_file(file, suffix)

        service = DocumentProcessingService()
        parsed_document = service.parse_and_enrich(
            file_path=temporary_path,
            original_filename=filename,
            storage_mode=storage_mode,
        )

        coordinator = SemanticCheckCoordinator()
        result = coordinator.run(
            document=parsed_document,
            vacancy_text=vacancy_text,
        )

        return result

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при семантической проверке документа: {error}",
        ) from error

    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()


@router.post("/report", response_model=Report)
async def build_document_report(
    file: UploadFile = File(...),
    vacancy_text: str | None = Form(None),
    storage_mode: StorageMode = Form(StorageMode.TEMPORARY),
    current_user: UserORM = Depends(require_candidate_or_hr_or_admin),
    db: Session = Depends(get_db),
) -> Report:
    """
    Загружает DOCX/PDF-файл, выполняет полный пайплайн проверки
    и формирует итоговый отчёт.

    Отчёт привязывается к текущему пользователю через owner_user_id.
    """

    filename = file.filename or ""
    suffix = _validate_file_suffix(filename)

    temporary_path: Path | None = None
    started_at = perf_counter()

    try:
        temporary_path = await _save_upload_to_temp_file(file, suffix)

        service = DocumentProcessingService()
        parsed_document = service.parse_and_enrich(
            file_path=temporary_path,
            original_filename=filename,
            storage_mode=storage_mode,
        )

        formal_coordinator = FormalCheckCoordinator()
        formal_check_response = formal_coordinator.run(parsed_document)

        semantic_coordinator = SemanticCheckCoordinator()
        semantic_check_response = semantic_coordinator.run(
            document=parsed_document,
            vacancy_text=vacancy_text,
        )

        report_builder = ReportBuilder()
        report = report_builder.build(
            document=parsed_document,
            formal_check_response=formal_check_response,
            semantic_check_response=semantic_check_response,
            vacancy_text=vacancy_text,
        )

        if storage_mode == StorageMode.NO_STORE:
            report.technical_info.metadata["saved_to_db"] = False
        else:
            report.technical_info.metadata["saved_to_db"] = True

            storage_service = ReportStorageService(db)
            storage_service.save_report(
                document=parsed_document,
                report=report,
                owner_user_id=current_user.id,
            )

        duration_ms = round((perf_counter() - started_at) * 1000, 3)

        metrics.record_document_processed(
            duration_ms=duration_ms,
            issues_count=report.total_issues,
        )
        metrics.record_report_generated()

        logger.info(
            "report_generated document_id=%s report_id=%s owner_user_id=%s issues=%s storage_mode=%s saved_to_db=%s duration_ms=%s",
            report.document_id,
            report.report_id,
            current_user.id,
            report.total_issues,
            storage_mode.value,
            report.technical_info.metadata.get("saved_to_db"),
            duration_ms,
        )

        return report

    except HTTPException:
        raise

    except Exception as error:
        metrics.record_error()
        logger.exception(
            "report_generation_failed filename_suffix=%s storage_mode=%s owner_user_id=%s",
            suffix,
            storage_mode.value,
            current_user.id,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при формировании отчёта: {error}",
        ) from error

    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()


@router.get("/reports/{report_id}", response_model=Report)
def get_saved_report(
    report_id: str,
    current_user: UserORM = Depends(require_candidate_or_hr_or_admin),
    db: Session = Depends(get_db),
) -> Report:
    """
    Возвращает сохранённый отчёт по report_id.

    Кандидат и HR могут получить только свои отчёты.
    Администратор может получить любой отчёт.
    """

    storage_service = ReportStorageService(db)

    _ensure_report_access(
        storage_service=storage_service,
        report_id=report_id,
        current_user=current_user,
    )

    report = storage_service.get_report(report_id)

    if report is None:
        raise HTTPException(
            status_code=404,
            detail="Отчёт не найден",
        )

    return report


@router.get("/reports/{report_id}/export/docx")
def export_saved_report_to_docx(
    report_id: str,
    current_user: UserORM = Depends(require_candidate_or_hr_or_admin),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """
    Экспорт сохранённого отчёта в DOCX.

    Кандидат и HR могут экспортировать только свои отчёты.
    Администратор может экспортировать любой отчёт.
    """

    storage_service = ReportStorageService(db)

    _ensure_report_access(
        storage_service=storage_service,
        report_id=report_id,
        current_user=current_user,
    )

    report = storage_service.get_report(report_id)

    if report is None:
        raise HTTPException(
            status_code=404,
            detail="Отчёт не найден",
        )

    exporter = DocxReportExporter()
    file_stream = exporter.export(report)

    safe_filename = f"report_{report.report_id}.docx"

    return StreamingResponse(
        file_stream,
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
        headers={
            "Content-Disposition": f'attachment; filename="{safe_filename}"'
        },
    )
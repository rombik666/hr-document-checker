from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.coordinator.formal_check_coordinator import FormalCheckCoordinator
from app.schemas.checks import FormalCheckResponse
from app.schemas.documents import ParsedDocument
from app.services.document_processing_service import DocumentProcessingService

from app.reports.report_builder import ReportBuilder
from app.schemas.reports import Report

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.report_storage_service import ReportStorageService


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


@router.post("/parse", response_model=ParsedDocument)
async def parse_document(file: UploadFile = File(...)) -> ParsedDocument:
    """
    Загружает DOCX/PDF-файл, извлекает текст, секции и сущности.
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
async def check_document_formally(file: UploadFile = File(...)) -> FormalCheckResponse:
    """
    Загружает DOCX/PDF-файл и выполняет формальные rule-based проверки.

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


@router.post("/report", response_model=Report)
async def build_document_report(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> Report:
    """
    Загружает DOCX/PDF-файл, выполняет первичную обработку,
    запускает формальные проверки и возвращает итоговый отчёт.
    
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
        )

        coordinator = FormalCheckCoordinator()
        formal_check_response = coordinator.run(parsed_document)

        report_builder = ReportBuilder()
        report = report_builder.build(
            document=parsed_document,
            formal_check_response=formal_check_response,
        )

        storage_service = ReportStorageService(db)
        storage_service.save_report(
            document=parsed_document,
            report=report,
        )

        return report

    except HTTPException:
        raise

    except Exception as error:
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
    db: Session = Depends(get_db),
) -> Report:
    """
    Возвращает сохранённый отчёт по report_id.
    
    """

    storage_service = ReportStorageService(db)
    report = storage_service.get_report(report_id)

    if report is None:
        raise HTTPException(
            status_code=404,
            detail="Отчёт не найден",
        )

    return report
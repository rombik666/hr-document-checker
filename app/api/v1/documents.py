from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.coordinator.formal_check_coordinator import FormalCheckCoordinator
from app.schemas.checks import FormalCheckResponse
from app.schemas.documents import ParsedDocument
from app.services.document_processing_service import DocumentProcessingService


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
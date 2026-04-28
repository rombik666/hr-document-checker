from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.coordinator.formal_check_coordinator import FormalCheckCoordinator
from app.coordinator.semantic_check_coordinator import SemanticCheckCoordinator
from app.db.session import get_db
from app.reports.report_builder import ReportBuilder
from app.schemas.common import StorageMode
from app.services.document_processing_service import DocumentProcessingService
from app.services.report_storage_service import ReportStorageService


router = APIRouter(prefix="/web", tags=["web"])

templates = Jinja2Templates(directory="app/web/templates")


def _validate_file_suffix(filename: str) -> str:
    suffix = Path(filename).suffix.lower()

    if suffix not in {".docx", ".pdf"}:
        raise ValueError("Поддерживаются только файлы .docx и .pdf")

    return suffix


async def _save_upload_to_temp_file(file: UploadFile, suffix: str) -> Path:
    with NamedTemporaryFile(delete=False, suffix=suffix) as temporary_file:
        content = await file.read()
        temporary_file.write(content)
        return Path(temporary_file.name)


@router.get("/", response_class=HTMLResponse)
def show_upload_form(request: Request) -> HTMLResponse:
    """
    HTML-страница загрузки документа.
    """

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={},
    )


@router.post("/report", response_class=HTMLResponse)
async def build_report_page(
    request: Request,
    file: UploadFile = File(...),
    vacancy_text: str | None = Form(None),
    storage_mode: StorageMode = Form(StorageMode.TEMPORARY),
    db: Session = Depends(get_db),
) -> HTMLResponse:

    filename = file.filename or ""
    temporary_path: Path | None = None

    try:
        suffix = _validate_file_suffix(filename)
        temporary_path = await _save_upload_to_temp_file(file, suffix)

        service = DocumentProcessingService()
        parsed_document = service.parse_and_enrich(
            file_path=temporary_path,
            original_filename=filename,
            storage_mode=storage_mode,
        )

        formal_check_response = FormalCheckCoordinator().run(parsed_document)

        semantic_check_response = SemanticCheckCoordinator().run(
            document=parsed_document,
            vacancy_text=vacancy_text,
        )

        report = ReportBuilder().build(
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
            )

        return templates.TemplateResponse(
            request=request,
            name="report.html",
            context={
                "report": report,
            },
        )

    except Exception as error:
        return templates.TemplateResponse(
            request=request,
            name="error.html",
            context={
                "error_message": str(error),
            },
            status_code=400,
        )

    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()
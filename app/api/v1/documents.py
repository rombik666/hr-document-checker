from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.parsers.parser_factory import ParserFactory
from app.schemas.documents import ParsedDocument
from app.extractors.entity_extractor import EntityExtractor
from app.extractors.section_classifier import SectionClassifier


router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/parse", response_model=ParsedDocument)
async def parse_document(file: UploadFile = File(...)) -> ParsedDocument:
    """
    Загружает DOCX/PDF-файл, сохраняет его во временный файл,
    выбирает подходящий парсер и возвращает ParsedDocument.
    """

    filename = file.filename or ""

    suffix = Path(filename).suffix.lower()

    if suffix not in {".docx", ".pdf"}:
        raise HTTPException(
            status_code=400,
            detail="Поддерживаются только файлы .docx и .pdf",
        )

    try:
        with NamedTemporaryFile(delete=False, suffix=suffix) as temporary_file:
            content = await file.read()
            temporary_file.write(content)
            temporary_path = Path(temporary_file.name)

        parser = ParserFactory.get_parser(temporary_path)
        parsed_document = parser.parse(temporary_path)

        # Возвращаем исходное имя файла, а не имя временного файла.
        parsed_document.metadata.filename = filename

        section_classifier = SectionClassifier()
        entity_extractor = EntityExtractor()

        parsed_document = section_classifier.classify(parsed_document)
        parsed_document = entity_extractor.enrich(parsed_document)

        return parsed_document

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при парсинге документа: {error}",
        ) from error

    finally:
        if "temporary_path" in locals() and temporary_path.exists():
            temporary_path.unlink()
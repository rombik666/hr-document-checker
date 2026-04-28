from pathlib import Path

from app.parsers.base import DocumentParser
from app.parsers.docx_parser import DOCXParser
from app.parsers.pdf_parser import PDFParser


class ParserFactory:
    """
    Фабрика парсеров.

    Она выбирает нужный парсер по расширению файла:
    .docx → DOCXParser
    .pdf  → PDFParser
    """

    @staticmethod
    def get_parser(file_path: Path) -> DocumentParser:
        suffix = file_path.suffix.lower()

        if suffix == ".docx":
            return DOCXParser()

        if suffix == ".pdf":
            return PDFParser()

        raise ValueError(
            f"Неподдерживаемый формат файла: {suffix}. "
            f"Поддерживаются только .docx и .pdf"
        )
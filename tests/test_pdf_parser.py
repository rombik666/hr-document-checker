from pathlib import Path

import fitz

from app.parsers.pdf_parser import PDFParser
from app.schemas.common import ProcessingStatus, SourceFormat


def test_pdf_parser_extracts_text(tmp_path: Path) -> None:

    file_path = tmp_path / "resume.pdf"

    pdf = fitz.open()
    page = pdf.new_page()
    page.insert_text((72, 72), "Ivan Ivanov\nPython developer\nExperience: 2 years")
    pdf.save(file_path)
    pdf.close()

    parser = PDFParser()
    parsed_document = parser.parse(file_path)

    assert parsed_document.metadata.filename == "resume.pdf"
    assert parsed_document.metadata.source_format == SourceFormat.PDF
    assert parsed_document.metadata.processing_status == ProcessingStatus.PARSED

    assert "Ivan Ivanov" in parsed_document.raw_text
    assert "Python developer" in parsed_document.raw_text
    assert "Experience: 2 years" in parsed_document.raw_text

    assert len(parsed_document.sections) >= 1
    assert parsed_document.sections[0].section_type == "page"

    assert parsed_document.metadata.warnings
    assert "PDF" in parsed_document.metadata.warnings[0]


def test_pdf_parser_raises_error_for_missing_file(tmp_path: Path) -> None:

    file_path = tmp_path / "missing.pdf"

    parser = PDFParser()

    try:
        parser.parse(file_path)
    except FileNotFoundError as error:
        assert "Файл не найден" in str(error)
    else:
        raise AssertionError("Ожидался FileNotFoundError")
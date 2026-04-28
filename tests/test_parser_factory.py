from pathlib import Path

from app.parsers.docx_parser import DOCXParser
from app.parsers.parser_factory import ParserFactory
from app.parsers.pdf_parser import PDFParser


def test_parser_factory_returns_docx_parser() -> None:
    """
    Проверяем, что для .docx выбирается DOCXParser.
    """

    parser = ParserFactory.get_parser(Path("resume.docx"))

    assert isinstance(parser, DOCXParser)


def test_parser_factory_returns_pdf_parser() -> None:
    """
    Проверяем, что для .pdf выбирается PDFParser.
    """

    parser = ParserFactory.get_parser(Path("resume.pdf"))

    assert isinstance(parser, PDFParser)


def test_parser_factory_rejects_unsupported_format() -> None:
    """
    Проверяем, что неподдерживаемый формат вызывает ошибку.
    """

    try:
        ParserFactory.get_parser(Path("resume.txt"))
    except ValueError as error:
        assert "Неподдерживаемый формат файла" in str(error)
    else:
        raise AssertionError("Ожидался ValueError")
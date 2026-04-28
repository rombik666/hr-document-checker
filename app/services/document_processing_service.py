from pathlib import Path

from app.extractors.entity_extractor import EntityExtractor
from app.extractors.section_classifier import SectionClassifier
from app.parsers.parser_factory import ParserFactory
from app.schemas.documents import ParsedDocument


class DocumentProcessingService:
    """
    Сервис первичной обработки документа.

    """

    def __init__(self) -> None:
        self.section_classifier = SectionClassifier()
        self.entity_extractor = EntityExtractor()

    def parse_and_enrich(
        self,
        file_path: Path,
        original_filename: str | None = None,
    ) -> ParsedDocument:
        parser = ParserFactory.get_parser(file_path)
        parsed_document = parser.parse(file_path)

        if original_filename:
            parsed_document.metadata.filename = original_filename

        parsed_document = self.section_classifier.classify(parsed_document)
        parsed_document = self.entity_extractor.enrich(parsed_document)

        return parsed_document
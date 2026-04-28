from pathlib import Path

from app.extractors.document_type_classifier import DocumentTypeClassifier
from app.extractors.entity_extractor import EntityExtractor
from app.extractors.section_classifier import SectionClassifier
from app.parsers.parser_factory import ParserFactory
from app.schemas.documents import ParsedDocument


class DocumentProcessingService:
    """
    Сервис первичной обработки документа.

    Делает:
    1. Выбор парсера.
    2. Парсинг файла.
    3. Определение типа документа.
    4. Классификацию секций.
    5. Извлечение сущностей.
    """

    def __init__(self) -> None:
        self.document_type_classifier = DocumentTypeClassifier()
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

        parsed_document = self.document_type_classifier.classify(parsed_document)
        parsed_document = self.section_classifier.classify(parsed_document)
        parsed_document = self.entity_extractor.enrich(parsed_document)

        return parsed_document
from app.extractors.contact_extractor import ContactExtractor
from app.extractors.date_extractor import DateExtractor
from app.extractors.skill_extractor import SkillExtractor
from app.extractors.url_extractor import URLExtractor
from app.schemas.documents import ExtractedEntity, ParsedDocument


class EntityExtractor:
    """
    Главный экстрактор сущностей.

    Он объединяет отдельные экстракторы:
    - ContactExtractor;
    - URLExtractor;
    - DateExtractor;
    - SkillExtractor.

    Его задача — взять ParsedDocument и заполнить поле entities.
    """

    def __init__(self) -> None:
        self.contact_extractor = ContactExtractor()
        self.url_extractor = URLExtractor()
        self.date_extractor = DateExtractor()
        self.skill_extractor = SkillExtractor()

    def enrich(self, parsed_document: ParsedDocument) -> ParsedDocument:
        all_entities: list[ExtractedEntity] = []

        if parsed_document.sections:
            for section in parsed_document.sections:
                all_entities.extend(
                    self._extract_from_text(
                        text=section.text,
                        source_section_id=section.section_id,
                    )
                )
        else:
            all_entities.extend(
                self._extract_from_text(
                    text=parsed_document.raw_text,
                    source_section_id=None,
                )
            )

        parsed_document.entities = self._deduplicate_entities(all_entities)

        return parsed_document

    def _extract_from_text(
        self,
        text: str,
        source_section_id: str | None,
    ) -> list[ExtractedEntity]:
        entities: list[ExtractedEntity] = []

        entities.extend(self.contact_extractor.extract(text, source_section_id))
        entities.extend(self.url_extractor.extract(text, source_section_id))
        entities.extend(self.date_extractor.extract(text, source_section_id))
        entities.extend(self.skill_extractor.extract(text, source_section_id))

        return entities

    @staticmethod
    def _deduplicate_entities(entities: list[ExtractedEntity]) -> list[ExtractedEntity]:
        """
        Убираем дубли по типу сущности и нормализованному значению.
        """

        unique: dict[tuple[str, str], ExtractedEntity] = {}

        for entity in entities:
            key = (
                entity.entity_type.value,
                entity.normalized_value or entity.value.lower(),
            )

            if key not in unique:
                unique[key] = entity

        return list(unique.values())
import re
from uuid import uuid4

from app.schemas.common import EntityType
from app.schemas.documents import ExtractedEntity


class ContactExtractor:
    """
    Извлекает контактные данные из текста:
    - e-mail;
    - телефон.
    
    """

    EMAIL_PATTERN = re.compile(
        r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b"
    )

    PHONE_PATTERN = re.compile(
        r"(?:(?:\+7|8)[\s\-()]*)?"
        r"(?:\(?\d{3}\)?[\s\-()]*)"
        r"\d{3}[\s\-]*\d{2}[\s\-]*\d{2}"
    )

    def extract(self, text: str, source_section_id: str | None = None) -> list[ExtractedEntity]:
        entities: list[ExtractedEntity] = []

        entities.extend(self.extract_emails(text, source_section_id))
        entities.extend(self.extract_phones(text, source_section_id))

        return entities

    def extract_emails(
        self,
        text: str,
        source_section_id: str | None = None,
    ) -> list[ExtractedEntity]:
        entities: list[ExtractedEntity] = []

        for match in self.EMAIL_PATTERN.finditer(text):
            value = match.group(0)
            normalized_value = value.lower()

            entities.append(
                ExtractedEntity(
                    entity_id=str(uuid4()),
                    entity_type=EntityType.EMAIL,
                    value=value,
                    normalized_value=normalized_value,
                    source_section_id=source_section_id,
                    start_char=match.start(),
                    end_char=match.end(),
                    confidence_score=1.0,
                    metadata={"extractor": "ContactExtractor"},
                )
            )

        return entities

    def extract_phones(
        self,
        text: str,
        source_section_id: str | None = None,
    ) -> list[ExtractedEntity]:
        entities: list[ExtractedEntity] = []

        for match in self.PHONE_PATTERN.finditer(text):
            value = match.group(0).strip()
            normalized_value = self._normalize_phone(value)

            entities.append(
                ExtractedEntity(
                    entity_id=str(uuid4()),
                    entity_type=EntityType.PHONE,
                    value=value,
                    normalized_value=normalized_value,
                    source_section_id=source_section_id,
                    start_char=match.start(),
                    end_char=match.end(),
                    confidence_score=0.95,
                    metadata={"extractor": "ContactExtractor"},
                )
            )

        return entities

    @staticmethod
    def _normalize_phone(phone: str) -> str:
        """
        Приводит телефон к более стабильному виду:
        +7 999 123-45-67 -> +79991234567
        8 (999) 123-45-67 -> +79991234567
        """

        digits = re.sub(r"\D", "", phone)

        if len(digits) == 11 and digits.startswith("8"):
            return "+7" + digits[1:]

        if len(digits) == 11 and digits.startswith("7"):
            return "+" + digits

        if len(digits) == 10:
            return "+7" + digits

        return digits
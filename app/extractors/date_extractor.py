import re
from uuid import uuid4

from app.schemas.common import EntityType
from app.schemas.documents import ExtractedEntity


class DateExtractor:
    """
    Извлекает даты и периоды из текста.

    """

    DATE_PATTERNS = [
        # 01.02.2024, 01/02/2024, 01-02-2024
        re.compile(r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b"),

        # 2020-2022, 2020 — 2022
        re.compile(r"\b(?:19|20)\d{2}\s*[—–-]\s*(?:(?:19|20)\d{2}|н\.в\.|наст\.?\s*время|по\s*наст\.?\s*время)\b", re.IGNORECASE),

        # май 2020, Январь 2021
        re.compile(
            r"\b(?:январь|февраль|март|апрель|май|июнь|июль|август|сентябрь|октябрь|ноябрь|декабрь|"
            r"января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+"
            r"(?:19|20)\d{2}\b",
            re.IGNORECASE,
        ),

        # просто год: 2024
        re.compile(r"\b(?:19|20)\d{2}\b"),
    ]

    def extract(self, text: str, source_section_id: str | None = None) -> list[ExtractedEntity]:
        entities: list[ExtractedEntity] = []
        seen_spans: set[tuple[int, int]] = set()

        for pattern in self.DATE_PATTERNS:
            for match in pattern.finditer(text):
                span = (match.start(), match.end())

                if span in seen_spans:
                    continue

                seen_spans.add(span)

                value = match.group(0)

                entities.append(
                    ExtractedEntity(
                        entity_id=str(uuid4()),
                        entity_type=EntityType.DATE,
                        value=value,
                        normalized_value=value.lower(),
                        source_section_id=source_section_id,
                        start_char=match.start(),
                        end_char=match.end(),
                        confidence_score=0.85,
                        metadata={"extractor": "DateExtractor"},
                    )
                )

        return entities
import re
from uuid import uuid4

from app.schemas.common import EntityType
from app.schemas.documents import ExtractedEntity


class URLExtractor:
    """
    Извлекает ссылки из текста:
    - https://github.com/user
    - http://example.com
    - www.example.com
    """

    URL_PATTERN = re.compile(
        r"\b(?:https?://|www\.)[^\s<>()]+",
        re.IGNORECASE,
    )

    def extract(self, text: str, source_section_id: str | None = None) -> list[ExtractedEntity]:
        entities: list[ExtractedEntity] = []

        for match in self.URL_PATTERN.finditer(text):
            value = match.group(0).rstrip(".,;)")
            normalized_value = self._normalize_url(value)

            entities.append(
                ExtractedEntity(
                    entity_id=str(uuid4()),
                    entity_type=EntityType.URL,
                    value=value,
                    normalized_value=normalized_value,
                    source_section_id=source_section_id,
                    start_char=match.start(),
                    end_char=match.start() + len(value),
                    confidence_score=0.95,
                    metadata={"extractor": "URLExtractor"},
                )
            )

        return entities

    @staticmethod
    def _normalize_url(url: str) -> str:
        if url.startswith("www."):
            return "https://" + url

        return url
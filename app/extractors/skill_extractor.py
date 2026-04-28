import re
from uuid import uuid4

from app.schemas.common import EntityType
from app.schemas.documents import ExtractedEntity


class SkillExtractor:
    """
    Извлекает навыки по заранее заданному словарю.

    """

    DEFAULT_SKILLS = [
        "python",
        "fastapi",
        "django",
        "flask",
        "postgresql",
        "mysql",
        "sqlite",
        "docker",
        "docker compose",
        "git",
        "linux",
        "rest api",
        "api",
        "html",
        "css",
        "javascript",
        "typescript",
        "react",
        "vue",
        "matlab",
        "machine learning",
        "ml",
        "deep learning",
        "rag",
        "llm",
        "pandas",
        "numpy",
        "pytorch",
        "tensorflow",
    ]

    def __init__(self, skills: list[str] | None = None) -> None:
        self.skills = skills or self.DEFAULT_SKILLS

    def extract(self, text: str, source_section_id: str | None = None) -> list[ExtractedEntity]:
        entities: list[ExtractedEntity] = []
        lower_text = text.lower()

        for skill in self.skills:
            pattern = self._build_skill_pattern(skill)

            for match in pattern.finditer(lower_text):
                value = text[match.start():match.end()]
                normalized_value = skill.lower()

                entities.append(
                    ExtractedEntity(
                        entity_id=str(uuid4()),
                        entity_type=EntityType.SKILL,
                        value=value,
                        normalized_value=normalized_value,
                        source_section_id=source_section_id,
                        start_char=match.start(),
                        end_char=match.end(),
                        confidence_score=0.8,
                        metadata={"extractor": "SkillExtractor"},
                    )
                )

        return self._deduplicate(entities)

    @staticmethod
    def _build_skill_pattern(skill: str) -> re.Pattern[str]:
        escaped_skill = re.escape(skill.lower())
        return re.compile(rf"(?<![a-zа-яё0-9]){escaped_skill}(?![a-zа-яё0-9])", re.IGNORECASE)

    @staticmethod
    def _deduplicate(entities: list[ExtractedEntity]) -> list[ExtractedEntity]:
        unique: dict[tuple[str, int, int], ExtractedEntity] = {}

        for entity in entities:
            key = (
                entity.normalized_value or entity.value.lower(),
                entity.start_char or -1,
                entity.end_char or -1,
            )
            unique[key] = entity

        return list(unique.values())
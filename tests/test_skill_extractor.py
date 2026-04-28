from app.extractors.skill_extractor import SkillExtractor
from app.schemas.common import EntityType


def test_skill_extractor_extracts_skills() -> None:
    text = "Навыки: Python, FastAPI, PostgreSQL, Docker, Git"

    extractor = SkillExtractor()
    entities = extractor.extract(text)

    skills = {entity.normalized_value for entity in entities}

    assert "python" in skills
    assert "fastapi" in skills
    assert "postgresql" in skills
    assert "docker" in skills
    assert "git" in skills

    assert all(entity.entity_type == EntityType.SKILL for entity in entities)


def test_skill_extractor_does_not_match_inside_words() -> None:
    text = "Я люблю apiculture и typography"

    extractor = SkillExtractor(skills=["api"])
    entities = extractor.extract(text)

    assert entities == []